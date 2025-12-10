from datetime import datetime, timezone

from fastapi import Body, Depends
from fastapi.responses import Response as FastAPIResponse

from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
from apps.authentication.deps import get_current_user
from apps.authentication.domain.recovery_code.public import RecoveryCodesListResponse
from apps.authentication.errors import MFAGlobalLockoutError, MFASessionNotFoundError, TooManyTOTPAttemptsError
from apps.authentication.services.mfa_session import MFASessionService
from apps.authentication.services.recovery_codes import (
    format_recovery_codes_text,
    generate_recovery_codes,
    get_recovery_codes,
)
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    MFADisableInitiateResponse,
    MFADisableVerifyRequest,
    MFADisableVerifyResponse,
    PublicUser,
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
    MFANotEnabledError,
    MFASessionPurposeMismatchError,
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
        prepared_data = UserCreate(**user_create_schema.dict())
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
            from apps.users.errors import MFAAlreadyEnabledError

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
            from apps.users.errors import MFAAlreadyEnabledError

            raise MFAAlreadyEnabledError()

        # Validate pending setup and get decrypted secret
        decrypted_secret = totp_service.validate_pending_setup(fresh_user)

        # Verify code (strict, no time-window tolerance for enrollment)
        is_valid = totp_service.verify_code(decrypted_secret, schema.code, valid_window=0)

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
        existing_codes = await RecoveryCodeCRUD(session).get_by_user_id(fresh_user.id)
        if len(existing_codes) == 0:
            codes = await generate_recovery_codes(session, fresh_user.id)

    result = TOTPVerifyResponse(
        message="TOTP MFA has been successfully enabled for your account.",
        mfa_enabled=True,
        recovery_codes=codes,
    )

    return Response(result=result)


async def user_mfa_totp_disable_initiate(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[MFADisableInitiateResponse]:
    """Initiate MFA disable: verify user has MFA enabled and create disable session."""
    # Check if user has MFA enabled
    if not user.mfa_secret:
        raise MFANotEnabledError()

    # Create MFA session for disable purpose
    mfa_service = MFASessionService()
    mfa_session_id = await mfa_service.create_session(user_id=user.id, purpose="disable")

    # Generate mfa_token
    mfa_token = AuthenticationService.create_mfa_token(mfa_session_id=mfa_session_id)

    logger.info(f"MFA disable initiated user_id={user.id} mfa_session_id={mfa_session_id}")

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
) -> Response[MFADisableVerifyResponse]:
    """Verify TOTP code and disable MFA (requires authentication and user validation)."""

    # Step 1: Validate mfa_token and get session data
    mfa_service = MFASessionService()
    mfa_session_id, token_user_id, purpose = await mfa_service.validate_and_get_session(schema.mfa_token)

    # Step 2: SECURITY - Validate current user matches token's user
    if user.id != token_user_id:
        logger.warning(f"MFA disable attempted with mismatched user current_user={user.id} token_user={token_user_id}")
        from fastapi import HTTPException
        from fastapi import status as http_status

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
        raise MFAGlobalLockoutError()

    # Step 5: Get session data to check per-session attempts
    session_data = await mfa_service.get_session(mfa_session_id)
    if not session_data:
        logger.warning(f"MFA session expired during verification mfa_session_id={mfa_session_id}")
        raise MFASessionNotFoundError()

    # Step 6: Check per-session max attempts
    max_attempts = settings.redis.mfa_max_attempts
    if session_data.has_exceeded_max_attempts(max_attempts):
        logger.warning(
            f"MFA disable blocked - max attempts exceeded user_id={token_user_id} "
            f"attempts={session_data.failed_totp_attempts}"
        )
        raise TooManyTOTPAttemptsError()

    # Step 7: Fetch user from database
    async with atomic(session):
        crud = UsersCRUD(session)
        db_user = await crud.get_by_id(token_user_id)

        # Step 8: Validate user has MFA enabled
        if not db_user.mfa_secret:
            logger.warning(f"MFA disable attempted but MFA not enabled user_id={token_user_id}")
            raise MFANotEnabledError()

        # Step 9: Decrypt TOTP secret
        decrypted_secret = totp_service.decrypt_secret(db_user.mfa_secret)

        # Step 10: Verify TOTP code with replay protection
        is_valid, time_step_used = totp_service.verify_with_replay_check(
            secret=decrypted_secret,
            code=schema.code,
            last_used_step=db_user.last_totp_time_step,
        )

        # Step 10: Handle verification failure
        if not is_valid:
            # Increment per-session attempts
            new_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)

            # Increment global attempts
            global_count = await mfa_service.increment_global_failed_attempts(token_user_id)

            logger.warning(
                f"Invalid TOTP code for MFA disable user_id={token_user_id} "
                f"session_attempts={new_count} global_attempts={global_count}"
            )

            # Check if global lockout threshold reached
            if global_count >= settings.redis.mfa_global_lockout_attempts:
                logger.warning(f"Global lockout threshold reached user_id={token_user_id}")
                # Note: Next attempt will be blocked by is_globally_locked_out check

            # Check if per-session threshold reached
            if new_count is not None and new_count >= settings.redis.mfa_max_attempts:
                await mfa_service.delete_session(mfa_session_id)
                logger.warning(f"MFA session deleted - max attempts exceeded mfa_session_id={mfa_session_id}")

            raise InvalidTOTPCodeError()

        # Step 11: Update last TOTP time step (replay protection)
        assert time_step_used is not None  # Guaranteed by is_valid=True
        await crud.update_last_totp_time_step(user_id=db_user.id, time_step=time_step_used)

        logger.info(f"TOTP verified for MFA disable user_id={token_user_id} time_step={time_step_used}")

        # Step 12: Disable MFA and clear all related fields
        disabled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await crud.disable_mfa(user_id=db_user.id, disabled_at=disabled_at)

        # Step 13: Invalidate all recovery codes (soft delete)
        recovery_crud = RecoveryCodeCRUD(session)
        await recovery_crud.delete_by_user_id(user_id=token_user_id)

        logger.info(f"MFA disabled and recovery codes invalidated user_id={token_user_id}")

    # Step 14: Clear global lockout (outside atomic block, Redis operation)
    await mfa_service.clear_global_lockout(token_user_id)

    # Step 15: Delete MFA session (cleanup)
    await mfa_service.delete_session(mfa_session_id)

    logger.info(f"MFA disable completed user_id={token_user_id}")

    # Step 16: Return success response
    return Response(
        result=MFADisableVerifyResponse(
            mfa_disabled=True,
            message="MFA has been successfully disabled for your account.",
        )
    )


async def user_get_recovery_codes(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[RecoveryCodesListResponse]:
    """Get list of recovery codes with their usage status.

    Returns all recovery codes for the authenticated user with:
    - Decrypted code values
    - Used/unused status for each code
    - When each code was used (if applicable)
    - Summary statistics (total and unused count)

    Requires MFA to be enabled.
    """
    # Refetch user to ensure latest MFA state
    fresh_user = await UsersCRUD(session).get_by_id(user.id)

    # Check MFA is enabled
    if not fresh_user.mfa_secret:
        raise MFANotEnabledError()

    # Get all recovery codes with decrypted values
    codes = await get_recovery_codes(session, fresh_user.id)

    # Check if recovery codes exist
    if not codes:
        raise RecoveryCodesNotFoundError()

    # Calculate statistics
    total = len(codes)
    unused = sum(1 for c in codes if not c.used)

    result = RecoveryCodesListResponse(
        codes=codes,
        total=total,
        unused_count=unused,
    )

    return Response(result=result)


async def user_download_recovery_codes(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> FastAPIResponse:
    """Download recovery codes as a text file.

    Returns a plain text file with all recovery codes and their usage status.
    The file includes:
    - User email and generation timestamp
    - Each code with usage status
    - Security warnings

    Requires MFA to be enabled.
    """
    # Refetch user to ensure latest MFA state
    fresh_user = await UsersCRUD(session).get_by_id(user.id)

    # Check MFA is enabled
    if not fresh_user.mfa_secret:
        raise MFANotEnabledError()

    # Get all recovery codes with decrypted values
    codes = await get_recovery_codes(session, fresh_user.id)

    # Check if recovery codes exist
    if not codes:
        raise RecoveryCodesNotFoundError()

    # Get user email for text file header
    email = fresh_user.email_encrypted or fresh_user.email

    # Format as downloadable text
    text_content = format_recovery_codes_text(codes, email)

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"recovery_codes_{timestamp}.txt"

    # Return as downloadable text file with security headers
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
