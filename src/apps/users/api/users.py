from datetime import datetime, timezone

from fastapi import Body, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from fastapi.responses import Response as FastAPIResponse

from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
from apps.authentication.deps import get_current_user
from apps.authentication.domain.recovery_code.public import RecoveryCodesListResponse
from apps.authentication.errors import MFAGlobalLockoutError, MFASessionNotFoundError, TooManyTOTPAttemptsError
from apps.authentication.services.mfa_helpers import extract_request_metadata
from apps.authentication.services.mfa_notifications import MFANotificationService
from apps.authentication.services.mfa_session import MFASessionService
from apps.authentication.services.recovery_codes import (
    format_recovery_codes_text,
    generate_recovery_codes,
    get_recovery_codes,
    send_recovery_code_notifications,
    verify_recovery_code_service,
)
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    MFADisableInitiateResponse,
    MFADisableVerifyRequest,
    MFADisableVerifyResponse,
    PublicUser,
    RecoveryCodesViewInitiateResponse,
    RecoveryCodesViewVerifyRequest,
    TOTPInitiateResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
    User,
    UserCreate,
    UserCreateRequest,
    UserDevice,
    UserDeviceCreate,
    UserUpdateRequest,
)
from apps.users.errors import (
    InvalidTOTPCodeError,
    MFAAlreadyEnabledError,
    MFANotEnabledError,
    MFASessionPurposeMismatchError,
    RecoveryCodeAlreadyUsedError,
    RecoveryCodeInvalidError,
    RecoveryCodeNotFoundError,
    RecoveryCodesNotFoundError,
)
from apps.users.services.totp import totp_service
from apps.users.services.user import UserService
from apps.users.services.user_device import UserDeviceService
from apps.workspaces.service.workspace import WorkspaceService
from config import settings
from infrastructure.database.core import atomic
from infrastructure.database.deps import get_session
from infrastructure.logger import logger


async def user_create(
    user_create_schema: UserCreateRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        service = UserService(session)
        prepared_data = UserCreate(**user_create_schema.model_dump())
        user = await service.create_user(prepared_data)
        # Create default workspace for new user
        await WorkspaceService(session, user.id).create_workspace_from_user(user)
    return Response(result=PublicUser.from_user(user))


async def user_retrieve(
    user: User = Depends(get_current_user),
) -> Response[PublicUser]:
    # Get public representation of the authenticated user
    public_user = PublicUser.from_user(user)

    return Response(result=public_user)


async def user_update(
    user: User = Depends(get_current_user),
    user_update_schema: UserUpdateRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        updated_user: User = await UsersCRUD(session).update(user, user_update_schema)

    # Create public representation of the internal user
    public_user = PublicUser.from_user(updated_user)

    return Response(result=public_user)


async def user_delete(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        await UsersCRUD(session).delete(user.id)


async def user_save_device(
    user: User = Depends(get_current_user),
    data: UserDeviceCreate = Body(...),
    session=Depends(get_session),
) -> Response[UserDevice]:
    async with atomic(session):
        device = await UserDeviceService(session, user.id).add_device(data)
    return Response(result=device)


async def user_mfa_totp_initiate(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[TOTPInitiateResponse]:
    """Start TOTP setup: create secret, store it encrypted, return provisioning URI."""
    async with atomic(session):
        # Prevent setup if MFA already enabled
        if user.mfa_enabled:
            raise MFAAlreadyEnabledError()

        # Generate a new TOTP secret
        secret = totp_service.generate_secret()

        # Encrypt the secret for storage
        encrypted_secret = totp_service.encrypt_secret(secret)

        # Store encrypted secret in pending_mfa_secret
        crud = UsersCRUD(session)
        await crud.update_pending_mfa(
            user_id=user.id,
            encrypted_secret=encrypted_secret,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        # Generate provisioning URI for QR code
        provisioning_uri = totp_service.generate_provisioning_uri(secret, user.email_encrypted or user.email)

        result = TOTPInitiateResponse(
            provisioning_uri=provisioning_uri,
            message="Scan the QR code with your authenticator app and enter the 6-digit code to verify setup",
        )

    return Response(result=result)


async def user_mfa_totp_verify(
    schema: TOTPVerifyRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[TOTPVerifyResponse]:
    """Verify TOTP code and enable MFA.

    Returns 10 recovery codes on first-time setup only (displayed once).
    """
    async with atomic(session):
        # Refetch user from database to ensure we have latest MFA state
        fresh_user = await UsersCRUD(session).get_by_id(user.id)

        # Prevent activation if MFA already enabled (race condition protection)
        if fresh_user.mfa_enabled:
            raise MFAAlreadyEnabledError()

        # Validate pending setup and get decrypted secret
        decrypted_secret = totp_service.validate_pending_setup(fresh_user)

        # Verify code with standard time-window tolerance
        is_valid = totp_service.verify_code(decrypted_secret, schema.code, valid_window=1)

        if not is_valid:
            raise InvalidTOTPCodeError()

        # Activate MFA atomically
        assert fresh_user.pending_mfa_secret is not None  # Already validated above
        await UsersCRUD(session).activate_mfa(
            user_id=fresh_user.id,
            encrypted_secret=fresh_user.pending_mfa_secret,
        )

        # Generate recovery codes on first-time MFA setup only
        # Check if codes actually exist in DB, not just if timestamp is set
        # (handles case where previous attempt set timestamp but failed to create codes)
        codes = None
        download_token = None
        existing_codes = await RecoveryCodeCRUD(session).get_by_user_id(fresh_user.id)
        if len(existing_codes) == 0:
            codes = await generate_recovery_codes(session, fresh_user.id)
            # Generate download token so user can download their codes immediately
            download_token = AuthenticationService.create_download_recovery_codes_token(fresh_user.id)
            logger.info(
                f"Recovery codes generated during MFA setup user_id={fresh_user.id} "
                f"download_token_expires_in={settings.mfa.download_token_expiration_seconds}s"
            )

        notification_service = MFANotificationService()
        await notification_service.send_mfa_enabled_notification(
            user=fresh_user,
            enabled_at=datetime.now(timezone.utc),
            recovery_codes_count=10,
        )

    result = TOTPVerifyResponse(
        message="TOTP MFA has been successfully enabled for your account.",
        mfa_enabled=True,
        recovery_codes=codes,
        download_token=download_token,
    )

    return Response(result=result)


async def user_mfa_totp_disable_initiate(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[MFADisableInitiateResponse]:
    """Initiate MFA disable: verify user has MFA enabled and create disable session."""
    async with atomic(session):
        # Refetch user from database to ensure we have latest MFA state
        crud = UsersCRUD(session)
        fresh_user = await crud.get_by_id(user.id)

        # Check if user has MFA enabled (race condition protection)
        if not fresh_user.mfa_enabled or not fresh_user.mfa_secret:
            raise MFANotEnabledError()

        # Create MFA session for disable purpose
        mfa_service = MFASessionService()
        mfa_session_id = await mfa_service.create_session(user_id=fresh_user.id, purpose="disable")

        # Generate mfa_token
        mfa_token = AuthenticationService.create_mfa_token(mfa_session_id=mfa_session_id)

        logger.info(f"MFA disable initiated user_id={fresh_user.id} mfa_session_id={mfa_session_id}")

    return Response(
        result=MFADisableInitiateResponse(
            mfa_required=True,
            mfa_token=mfa_token,
            message="Please verify your identity by entering your TOTP code or recovery code to disable MFA",
        )
    )


async def user_mfa_totp_disable_verify(
    schema: MFADisableVerifyRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    request: Request = None,
) -> Response[MFADisableVerifyResponse]:
    """Verify TOTP code or recovery code and disable MFA.

    Accepts either a TOTP code (preferred) or a recovery code as verification.
    After successful verification, disables MFA and invalidates all recovery codes.
    """

    # Step 1: Validate mfa_token and get session data
    mfa_service = MFASessionService()
    mfa_session_id, token_user_id, purpose = await mfa_service.validate_and_get_session(schema.mfa_token)

    # Step 2: SECURITY - Validate current user matches token's user
    if user.id != token_user_id:
        logger.warning(f"MFA disable attempted with mismatched user current_user={user.id} token_user={token_user_id}")
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="This MFA token belongs to a different user"
        )

    # Step 3: Validate session purpose is "disable"
    if purpose != "disable":
        logger.warning(f"MFA session purpose mismatch user_id={token_user_id} expected=disable actual={purpose}")
        raise MFASessionPurposeMismatchError()

    # Step 4: Check global lockout
    is_locked = await mfa_service.is_globally_locked_out(token_user_id)
    if is_locked:
        logger.warning(f"MFA disable blocked - global lockout user_id={token_user_id}")
        raise MFAGlobalLockoutError(
            global_attempts_remaining=0,
        )

    # Step 5: Get session data to check per-session attempts
    session_data = await mfa_service.get_session(mfa_session_id)
    if not session_data:
        logger.warning(f"MFA session expired during verification mfa_session_id={mfa_session_id}")
        raise MFASessionNotFoundError()

    # Step 6: Check per-session max attempts
    max_attempts = settings.redis.mfa_max_attempts
    if session_data.has_exceeded_max_attempts(max_attempts):
        global_remaining = await mfa_service.get_remaining_global_attempts(token_user_id)
        logger.warning(
            f"MFA disable blocked - max attempts exceeded user_id={token_user_id} "
            f"attempts={session_data.failed_totp_attempts}"
        )
        raise TooManyTOTPAttemptsError(
            session_attempts_remaining=0,
            global_attempts_remaining=global_remaining,
            lockout_reason="session_limit",
        )

    # Step 7-11: Single atomic transaction for all database operations
    async with atomic(session):
        # Fetch user from database
        crud = UsersCRUD(session)
        db_user = await crud.get_by_id(token_user_id)

        # Validate user has MFA enabled (race condition protection)
        if not db_user.mfa_enabled or not db_user.mfa_secret:
            logger.warning(
                f"MFA disable attempted but MFA not enabled user_id={token_user_id} "
                f"mfa_enabled={db_user.mfa_enabled} has_secret={bool(db_user.mfa_secret)}"
            )
            raise MFANotEnabledError()

        # Try TOTP verification first
        # Decrypt TOTP secret
        decrypted_secret = totp_service.decrypt_secret(db_user.mfa_secret)

        # Verify TOTP code with replay protection
        is_valid, time_step_used = totp_service.verify_with_replay_check(
            secret=decrypted_secret,
            code=schema.code,
            last_used_step=db_user.last_totp_time_step,
        )

        if is_valid:
            # Update last TOTP time step immediately (replay protection)
            assert time_step_used is not None
            await crud.update_last_totp_time_step(user_id=db_user.id, time_step=time_step_used)
            logger.info(f"TOTP verified for MFA disable user_id={token_user_id} time_step={time_step_used}")
        else:
            # TOTP failed, try recovery code verification
            try:
                await verify_recovery_code_service(session, token_user_id, schema.code)
                
                # Send recovery code notifications (used + warning if needed)
                request_metadata = extract_request_metadata(request)
                await send_recovery_code_notifications(
                    session=session,
                    user=db_user,
                    used_at=datetime.now(timezone.utc),
                    request_info=request_metadata,
                )
                
                logger.info(f"Recovery code verified for MFA disable user_id={token_user_id}")
            except (
                RecoveryCodeInvalidError,
                RecoveryCodeAlreadyUsedError,
                RecoveryCodesNotFoundError,
                RecoveryCodeNotFoundError,
            ):
                # Both TOTP and recovery code failed - increment counters
                new_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)
                global_count = await mfa_service.increment_global_failed_attempts(token_user_id)

                # Calculate remaining attempts using service methods
                session_remaining = await mfa_service.get_remaining_session_attempts(mfa_session_id)
                global_remaining = await mfa_service.get_remaining_global_attempts(token_user_id)

                logger.warning(
                    f"Invalid TOTP/recovery code for MFA disable user_id={token_user_id} "
                    f"session_attempts={new_count} global_attempts={global_count}"
                )

                # Check if global lockout threshold reached
                if global_count >= settings.redis.mfa_global_lockout_attempts:
                    logger.warning(f"Global lockout threshold reached user_id={token_user_id}")

                # Check if per-session threshold reached
                if new_count is not None and new_count >= settings.redis.mfa_max_attempts:
                    await mfa_service.delete_session(mfa_session_id)
                    logger.warning(f"MFA session deleted - max attempts exceeded mfa_session_id={mfa_session_id}")

                # Send failed disable attempt notification
                if global_count >= settings.mfa.disable_failed_attempts_warning_threshold:
                    notification_service = MFANotificationService()
                    await notification_service.send_disable_failed_attempts_warning(
                        user=db_user,
                        failed_attempts=global_count,
                        attempted_at=datetime.now(timezone.utc),
                    )

                raise InvalidTOTPCodeError(
                    session_attempts_remaining=session_remaining,
                    global_attempts_remaining=global_remaining,
                )

        # Disable MFA and clear all related fields
        disabled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await crud.disable_mfa(user_id=db_user.id, disabled_at=disabled_at)

        # Invalidate all recovery codes (soft delete)
        recovery_crud = RecoveryCodeCRUD(session)
        await recovery_crud.delete_by_user_id(user_id=token_user_id)

        logger.info(f"MFA disabled and recovery codes invalidated user_id={token_user_id}")

    # Step 12: Clear global lockout (outside atomic block, Redis operation)
    await mfa_service.clear_global_lockout(token_user_id)

    # Step 13: Delete MFA session (cleanup)
    await mfa_service.delete_session(mfa_session_id)

    # Step 14: Send MFA disabled notification
    notification_service = MFANotificationService()
    await notification_service.send_mfa_disabled_notification(
        user=db_user,
        disabled_at=datetime.now(timezone.utc),
    )

    logger.info(f"MFA disable completed user_id={token_user_id}")

    # Step 15: Return success response
    return Response(
        result=MFADisableVerifyResponse(
            mfa_disabled=True,
            message="MFA has been successfully disabled for your account.",
        )
    )


async def user_recovery_codes_view_initiate(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[RecoveryCodesViewInitiateResponse]:
    """Initiate recovery codes viewing: verify user has MFA enabled and create verification session.

    This is the first step of the two-step TOTP-protected recovery codes view flow.
    Returns an mfa_token that must be used with a TOTP code to view recovery codes.

    Requires:
    - User is authenticated
    - MFA is enabled
    - Recovery codes exist

    Returns:
    - mfa_token: JWT token for the verification session
    - message: Instructions for next step
    """
    async with atomic(session):
        # Refetch user from database to ensure we have latest MFA state
        crud = UsersCRUD(session)
        fresh_user = await crud.get_by_id(user.id)

        # Check if user has MFA enabled (race condition protection)
        if not fresh_user.mfa_enabled or not fresh_user.mfa_secret:
            raise MFANotEnabledError()

        # Check if recovery codes exist
        recovery_crud = RecoveryCodeCRUD(session)
        existing_codes = await recovery_crud.get_by_user_id(fresh_user.id)
        if not existing_codes:
            raise RecoveryCodesNotFoundError()

        # Create MFA session for view purpose
        mfa_service = MFASessionService()
        mfa_session_id = await mfa_service.create_session(user_id=fresh_user.id, purpose="view_recovery_codes")

        # Generate mfa_token
        mfa_token = AuthenticationService.create_mfa_token(mfa_session_id=mfa_session_id)

        logger.info(f"Recovery codes view initiated user_id={fresh_user.id} mfa_session_id={mfa_session_id}")

    return Response(
        result=RecoveryCodesViewInitiateResponse(
            mfa_required=True,
            mfa_token=mfa_token,
            message="Please enter your TOTP code or a recovery code to view your recovery codes",
        )
    )


async def user_recovery_codes_view_verify(
    schema: RecoveryCodesViewVerifyRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[RecoveryCodesListResponse]:
    """Verify TOTP code or recovery code and return recovery codes with download token.

    This is the second step of the two-step MFA-protected recovery codes view flow.
    After successful verification (TOTP or recovery code), returns recovery codes and a short-lived download token.

    Security features:
    - TOTP replay protection
    - Recovery code single-use enforcement
    - Rate limiting (per-session and global)
    - Lockout protection
    - User validation

    Returns:
    - codes: List of recovery codes with usage status
    - download_token: Short-lived JWT (5 min) for downloading codes
    """
    # Step 1: Validate mfa_token and get session data
    mfa_service = MFASessionService()
    mfa_session_id, token_user_id, purpose = await mfa_service.validate_and_get_session(schema.mfa_token)

    # Step 2: SECURITY - Validate current user matches token's user
    if user.id != token_user_id:
        logger.warning(
            f"Recovery codes view attempted with mismatched user current_user={user.id} token_user={token_user_id}"
        )
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="This MFA token belongs to a different user"
        )

    # Step 3: Validate session purpose is "view_recovery_codes"
    if purpose != "view_recovery_codes":
        logger.warning(
            f"MFA session purpose mismatch user_id={token_user_id} expected=view_recovery_codes actual={purpose}"
        )
        raise MFASessionPurposeMismatchError()

    # Step 4: Check global lockout
    is_locked = await mfa_service.is_globally_locked_out(token_user_id)
    if is_locked:
        logger.warning(f"Recovery codes view blocked - global lockout user_id={token_user_id}")
        raise MFAGlobalLockoutError(
            global_attempts_remaining=0,
        )

    # Step 5: Get session data to check per-session attempts
    session_data = await mfa_service.get_session(mfa_session_id)
    if not session_data:
        logger.warning(f"MFA session expired during verification mfa_session_id={mfa_session_id}")
        raise MFASessionNotFoundError()

    # Step 6: Check per-session max attempts
    max_attempts = settings.redis.mfa_max_attempts
    if session_data.has_exceeded_max_attempts(max_attempts):
        global_remaining = await mfa_service.get_remaining_global_attempts(token_user_id)
        logger.warning(
            f"Recovery codes view blocked - max attempts exceeded user_id={token_user_id} "
            f"attempts={session_data.failed_totp_attempts}"
        )
        raise TooManyTOTPAttemptsError(
            session_attempts_remaining=0,
            global_attempts_remaining=global_remaining,
            lockout_reason="session_limit",
        )

    # Step 7: Fetch user from database
    async with atomic(session):
        crud = UsersCRUD(session)
        db_user = await crud.get_by_id(token_user_id)

        # Step 8: Validate user has MFA enabled (race condition protection)
        if not db_user.mfa_enabled or not db_user.mfa_secret:
            logger.warning(
                f"Recovery codes view attempted but MFA not enabled user_id={token_user_id} "
                f"mfa_enabled={db_user.mfa_enabled} has_secret={bool(db_user.mfa_secret)}"
            )
            raise MFANotEnabledError()

        # Step 9: Try TOTP verification first
        verification_method = None

        # Decrypt TOTP secret
        decrypted_secret = totp_service.decrypt_secret(db_user.mfa_secret)

        # Verify TOTP code with replay protection
        is_valid, time_step_used = totp_service.verify_with_replay_check(
            secret=decrypted_secret,
            code=schema.code,
            last_used_step=db_user.last_totp_time_step,
        )

        if is_valid:
            verification_method = "totp"
            # Update last TOTP time step (replay protection)
            assert time_step_used is not None
            await crud.update_last_totp_time_step(user_id=db_user.id, time_step=time_step_used)
            logger.info(f"TOTP verified for recovery codes view user_id={token_user_id} time_step={time_step_used}")
        else:
            # Step 10: TOTP failed, try recovery code verification
            try:
                await verify_recovery_code_service(session, token_user_id, schema.code)
                verification_method = "recovery_code"
                logger.info(f"Recovery code verified for recovery codes view user_id={token_user_id}")
            except (
                RecoveryCodeInvalidError,
                RecoveryCodeAlreadyUsedError,
                RecoveryCodesNotFoundError,
                RecoveryCodeNotFoundError,
            ):
                # Both TOTP and recovery code failed - increment counters and raise error
                new_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)
                global_count = await mfa_service.increment_global_failed_attempts(token_user_id)

                # Calculate remaining attempts using service methods
                session_remaining = await mfa_service.get_remaining_session_attempts(mfa_session_id)
                global_remaining = await mfa_service.get_remaining_global_attempts(token_user_id)

                logger.warning(
                    f"Invalid TOTP/recovery code for recovery codes view user_id={token_user_id} "
                    f"session_attempts={new_count} global_attempts={global_count}"
                )

                # Check if global lockout threshold reached
                if global_count >= settings.redis.mfa_global_lockout_attempts:
                    logger.warning(f"Global lockout threshold reached user_id={token_user_id}")

                # Check if per-session threshold reached
                if new_count is not None and new_count >= settings.redis.mfa_max_attempts:
                    await mfa_service.delete_session(mfa_session_id)
                    logger.warning(f"MFA session deleted - max attempts exceeded mfa_session_id={mfa_session_id}")

                raise InvalidTOTPCodeError(
                    session_attempts_remaining=session_remaining,
                    global_attempts_remaining=global_remaining,
                )

        # Step 11: Get recovery codes with decrypted values
        codes = await get_recovery_codes(session, db_user.id)

        # Check if recovery codes exist
        if not codes:
            raise RecoveryCodesNotFoundError()

        # Step 12: Generate download token (short-lived, 5 minutes)
        download_token = AuthenticationService.create_download_recovery_codes_token(token_user_id)

        logger.info(
            f"Download token generated for recovery codes user_id={token_user_id} "
            f"verification_method={verification_method} "
            f"expires_in={settings.mfa.download_token_expiration_seconds}s"
        )

        # Calculate statistics
        total = len(codes)
        unused = sum(1 for c in codes if not c.used)

    # Step 13: Clear global lockout (outside atomic block, Redis operation)
    await mfa_service.clear_global_lockout(token_user_id)

    # Step 14: Delete MFA session (cleanup)
    await mfa_service.delete_session(mfa_session_id)

    # Step 15: Send notifications based on verification method
    notification_service = MFANotificationService()
    viewed_at = datetime.now(timezone.utc)

    if verification_method == "recovery_code":
        # Send recovery code notifications (used + warning if needed)
        await send_recovery_code_notifications(
            session=session,
            user=db_user,
            used_at=viewed_at,
            request_info=None,
        )
        # Also send recovery codes viewed notification
        await notification_service.send_recovery_codes_viewed_notification(
            user=db_user,
            viewed_at=viewed_at,
        )
    else:
        await notification_service.send_recovery_codes_viewed_notification(
            user=db_user,
            viewed_at=viewed_at,
        )

    logger.info(f"Recovery codes view completed user_id={token_user_id}")

    # Step 16: Return recovery codes with download token
    result = RecoveryCodesListResponse(
        codes=codes,
        total=total,
        unused_count=unused,
        download_token=download_token,
    )

    return Response(result=result)


async def user_download_recovery_codes(
    download_token: str = Query(..., description="Short-lived download token obtained from view/verify endpoint"),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> FastAPIResponse:
    """Download recovery codes as a text file.

    Returns a plain text file with all recovery codes and their usage status.
    The file includes:
    - User email and generation timestamp
    - Each code with usage status
    - Security warnings

    Security:
    - Requires valid download_token (5 min expiry) from view/verify endpoint
    - Token must match authenticated user
    - Validates MFA is enabled and recovery codes exist
    """
    # Step 1: Validate download token and extract user_id
    try:
        token_user_id = AuthenticationService.validate_download_recovery_codes_token(download_token)
    except Exception as e:
        logger.warning(f"Invalid download token user_id={user.id} error={str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired download token. Please verify your TOTP code again to get a new token.",
        )

    # Step 2: SECURITY - Validate current user matches token's user
    if user.id != token_user_id:
        logger.warning(f"Download token user mismatch current_user={user.id} token_user={token_user_id}")
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="This download token belongs to a different user"
        )

    # Step 3: Refetch user to ensure latest MFA state
    fresh_user = await UsersCRUD(session).get_by_id(user.id)

    # Step 4: Check MFA is enabled (race condition protection)
    if not fresh_user.mfa_secret:
        raise MFANotEnabledError()

    # Step 5: Get all recovery codes with decrypted values
    codes = await get_recovery_codes(session, fresh_user.id)

    # Step 6: Check if recovery codes exist
    if not codes:
        raise RecoveryCodesNotFoundError()

    # Step 7: Get user email for text file header
    email = fresh_user.email_encrypted or fresh_user.email

    # Step 8: Format as downloadable text
    text_content = format_recovery_codes_text(codes, email)

    # Step 9: Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"recovery_codes_{timestamp}.txt"

    logger.info(f"Recovery codes downloaded user_id={user.id} filename={filename}")

    # Step 10: Send downloaded notification
    notification_service = MFANotificationService()
    await notification_service.send_recovery_codes_downloaded_notification(
        user=fresh_user,
        downloaded_at=datetime.now(timezone.utc),
    )

    # Step 11: Return as downloadable text file with security headers
    return FastAPIResponse(
        content=text_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
        },
    )
