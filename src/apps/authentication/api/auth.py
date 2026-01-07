import uuid
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Body, Depends, Header, Request
from pydantic import ValidationError

from apps.authentication.deps import get_current_token, get_current_user
from apps.authentication.domain.login import MFARequiredResponse, MFATOTPVerifyRequest, UserLogin, UserLoginRequest
from apps.authentication.domain.logout import UserLogoutRequest
from apps.authentication.domain.recovery_code import RecoveryCodeVerifyRequest
from apps.authentication.domain.token import (
    InternalToken,
    JWTClaim,
    RefreshAccessTokenRequest,
    Token,
    TokenPayload,
    TokenPurpose,
)
from apps.authentication.errors import (
    AuthenticationError,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidTOTPCodeError,
    MFAGlobalLockoutError,
    MFASessionNotFoundError,
    MFATokenExpiredError,
    MFATokenInvalidError,
    MFATokenMalformedError,
    TooManyTOTPAttemptsError,
)
from apps.authentication.services.mfa_helpers import extract_request_metadata
from apps.authentication.services.mfa_notifications import MFANotificationService
from apps.authentication.services.mfa_session import MFASessionService
from apps.authentication.services.recovery_codes import send_recovery_code_notifications, verify_recovery_code_service
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.response import EmptyResponse
from apps.users import UsersCRUD
from apps.users.domain import AppInfoOS, PublicUser, User, UserDeviceCreate
from apps.users.errors import RecoveryCodeInvalidError, RecoveryCodeNotFoundError, UserNotFound
from apps.users.services.totp import TOTPService
from apps.users.services.user_device import UserDeviceService
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session
from infrastructure.logger import logger


async def get_token(
    user_login_schema: UserLoginRequest = Body(...),
    session=Depends(get_session),
    os_name: Annotated[str | None, Header()] = None,
    os_version: Annotated[str | None, Header()] = None,
    app_version: Annotated[str | None, Header()] = None,
) -> Response[UserLogin | MFARequiredResponse]:
    """Generate the JWT access token."""
    async with atomic(session):
        try:
            user: User = await AuthenticationService(session).authenticate_user(user_login_schema)
            if user_login_schema.device_id:
                await UserDeviceService(session, user.id).add_device(
                    UserDeviceCreate(
                        device_id=user_login_schema.device_id,
                        os=AppInfoOS(name=os_name, version=os_version) if os_name and os_version else None,
                        app_version=app_version,
                    )
                )
        except UserNotFound:
            raise InvalidCredentials(email=user_login_schema.email)

        if user.email_encrypted != user_login_schema.email:
            user = await UsersCRUD(session).update_encrypted_email(user, user_login_schema.email)

    # Check if user has MFA enabled
    if user.mfa_secret:
        # User has MFA enabled - return requirement response
        mfa_service = MFASessionService()
        mfa_session_id = await mfa_service.create_session(user_id=user.id)
        logger.info(f"MFA required for login user_id={user.id} email={user.email_encrypted}")
        mfa_token = AuthenticationService.create_mfa_token(mfa_session_id=mfa_session_id)
        return Response(
            result=MFARequiredResponse(
                mfa_required=True,
                mfa_session_id=mfa_session_id,
                mfa_token=mfa_token,
            )
        )

    rjti = str(uuid.uuid4())
    refresh_token = AuthenticationService.create_refresh_token({JWTClaim.sub: str(user.id), JWTClaim.jti: rjti})

    access_token = AuthenticationService.create_access_token(
        {
            JWTClaim.sub: str(user.id),
            JWTClaim.rjti: rjti,
        }
    )

    token = Token(access_token=access_token, refresh_token=refresh_token)
    public_user = PublicUser.from_user(user)

    return Response(
        result=UserLogin(
            token=token,
            user=public_user,
        )
    )


async def verify_mfa_totp(
    verify_request: MFATOTPVerifyRequest = Body(...),
    session=Depends(get_session),
    os_name: Annotated[str | None, Header()] = None,
    os_version: Annotated[str | None, Header()] = None,
    app_version: Annotated[str | None, Header()] = None,
) -> Response[UserLogin]:
    """Verify TOTP code during MFA and return tokens."""
    # Validate MFA token and get session info
    mfa_service = MFASessionService()
    try:
        mfa_session_id, user_id, purpose = await mfa_service.validate_and_get_session(verify_request.mfa_token)
    except (
        MFATokenExpiredError,
        MFATokenMalformedError,
        MFATokenInvalidError,
        MFASessionNotFoundError,
    ) as e:
        # Re-raise specific MFA token/session errors with detailed feedback
        raise e

    # Check global lockout FIRST (prevents bypassing per-session limits)
    is_locked = await mfa_service.is_globally_locked_out(user_id)
    if is_locked:
        logger.warning(f"User globally locked out from MFA attempts user_id={user_id}")
        await mfa_service.delete_session(mfa_session_id)
        raise MFAGlobalLockoutError(
            global_attempts_remaining=0,
        )

    # Check if max attempts exceeded BEFORE attempting verification
    session_data = await mfa_service.get_session(mfa_session_id)
    if session_data and session_data.has_exceeded_max_attempts(settings.redis.mfa_max_attempts):
        global_remaining = await mfa_service.get_remaining_global_attempts(user_id)
        logger.warning(
            f"MFA max attempts exceeded user_id={user_id} "
            f"failed_attempts={session_data.failed_totp_attempts} max_attempts={settings.redis.mfa_max_attempts}"
        )
        # Delete session to force re-login
        await mfa_service.delete_session(mfa_session_id)
        raise TooManyTOTPAttemptsError(
            session_attempts_remaining=0,
            global_attempts_remaining=global_remaining,
            lockout_reason="session_limit",
        )

    # Get user from DB
    async with atomic(session):
        user: User = await UsersCRUD(session).get_by_id(user_id)

        if not user.mfa_secret:
            # Edge case: user disabled MFA between login and verification
            raise MFATokenInvalidError()

        totp_service = TOTPService()

        # Verify TOTP code with replay protection
        try:
            decrypted_secret = totp_service.decrypt_secret(user.mfa_secret)
        except Exception:
            raise InvalidTOTPCodeError()

        # Get user's last used time step for replay protection
        last_step = user.last_totp_time_step

        # Verify with replay protection
        is_valid, time_step_used = totp_service.verify_with_replay_check(
            secret=decrypted_secret, code=verify_request.totp_code, last_used_step=last_step
        )

        if not is_valid:
            # Increment both per-session and global failed attempts counters
            new_attempt_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)
            global_attempt_count = await mfa_service.increment_global_failed_attempts(user.id)

            # Calculate remaining attempts using service methods
            session_remaining = await mfa_service.get_remaining_session_attempts(mfa_session_id)
            global_remaining = await mfa_service.get_remaining_global_attempts(user.id)

            logger.warning(
                f"Invalid TOTP code provided user_id={user.id} email={user.email_encrypted} "
                f"failed_attempts={new_attempt_count} global_failed_attempts={global_attempt_count}"
            )

            # Send warning email if global attempts hit threshold
            if global_attempt_count == settings.mfa.failed_attempts_warning_threshold:
                notification_service = MFANotificationService()
                await notification_service.send_failed_attempts_warning(
                    user=user,
                    failed_attempts=global_attempt_count,
                    max_attempts=settings.redis.mfa_global_lockout_attempts,
                )

            # Check if global lockout threshold reached
            if global_attempt_count >= settings.redis.mfa_global_lockout_attempts:
                logger.warning(
                    f"User globally locked out after max failed attempts user_id={user.id} "
                    f"email={user.email_encrypted} global_failed_attempts={global_attempt_count}"
                )
                await mfa_service.delete_session(mfa_session_id)

                # Send account locked notification
                notification_service = MFANotificationService()
                await notification_service.send_account_locked_email(
                    user=user,
                    lockout_reason="Too many failed MFA verification attempts",
                    failed_attempts=global_attempt_count,
                    lockout_ttl_seconds=settings.redis.mfa_global_lockout_ttl,
                )

                raise MFAGlobalLockoutError(
                    global_attempts_remaining=0,
                )

            # If this was the last allowed attempt for this session, delete session
            if new_attempt_count is not None and new_attempt_count >= settings.redis.mfa_max_attempts:
                logger.warning(
                    f"User locked out after max failed TOTP attempts for session user_id={user.id} "
                    f"email={user.email_encrypted} failed_attempts={new_attempt_count}"
                )
                await mfa_service.delete_session(mfa_session_id)
                raise TooManyTOTPAttemptsError(
                    session_attempts_remaining=0,
                    global_attempts_remaining=global_remaining,
                    lockout_reason="session_limit",
                )

            # Otherwise, raise normal invalid code error with remaining attempts
            raise InvalidTOTPCodeError(
                session_attempts_remaining=session_remaining,
                global_attempts_remaining=global_remaining,
            )

        # TOTP is valid - Update last used time step for replay protection
        assert time_step_used is not None  # Always set when is_valid is True
        await UsersCRUD(session).update_last_totp_time_step(user.id, time_step_used)

        # Clear global lockout counter and delete MFA session
        await mfa_service.clear_global_lockout(user.id)
        await mfa_service.delete_session(mfa_session_id)

        logger.info(
            f"MFA verification successful user_id={user.id} email={user.email_encrypted} "
            f"device_id={verify_request.device_id}"
        )

        # Register device if device_id provided
        if verify_request.device_id:
            await UserDeviceService(session, user.id).add_device(
                UserDeviceCreate(
                    device_id=verify_request.device_id,
                    os=AppInfoOS(name=os_name, version=os_version) if os_name and os_version else None,
                    app_version=app_version,
                )
            )

        # Issue refresh and access tokens
        rjti = str(uuid.uuid4())
        refresh_token = AuthenticationService.create_refresh_token({JWTClaim.sub: str(user.id), JWTClaim.jti: rjti})

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(user.id),
                JWTClaim.rjti: rjti,
            }
        )

    token = Token(access_token=access_token, refresh_token=refresh_token)
    public_user = PublicUser.from_user(user)

    return Response(
        result=UserLogin(
            token=token,
            user=public_user,
        )
    )


async def verify_mfa_recovery_code(
    request: Request,
    verify_request: RecoveryCodeVerifyRequest = Body(...),
    session=Depends(get_session),
    os_name: Annotated[str | None, Header()] = None,
    os_version: Annotated[str | None, Header()] = None,
    app_version: Annotated[str | None, Header()] = None,
) -> Response[UserLogin]:
    """Verify recovery code during MFA and return tokens."""
    # Validate MFA token and get session info
    mfa_service = MFASessionService()
    try:
        mfa_session_id, user_id, purpose = await mfa_service.validate_and_get_session(verify_request.mfa_token)
    except (
        MFATokenExpiredError,
        MFATokenMalformedError,
        MFATokenInvalidError,
        MFASessionNotFoundError,
    ) as e:
        # Re-raise specific MFA token/session errors with detailed feedback
        raise e

    # Check global lockout FIRST (prevents bypassing per-session limits)
    is_locked = await mfa_service.is_globally_locked_out(user_id)
    if is_locked:
        logger.warning(f"User globally locked out from MFA attempts user_id={user_id}")
        raise MFAGlobalLockoutError(
            global_attempts_remaining=0,
        )

    # Check if max per-session attempts exceeded BEFORE attempting verification
    session_data = await mfa_service.get_session(mfa_session_id)
    if session_data and session_data.has_exceeded_max_attempts(settings.redis.mfa_max_attempts):
        global_remaining = await mfa_service.get_remaining_global_attempts(user_id)
        logger.warning(
            f"MFA max attempts exceeded user_id={user_id} "
            f"failed_attempts={session_data.failed_totp_attempts} max_attempts={settings.redis.mfa_max_attempts}"
        )
        # Delete session to force re-login
        await mfa_service.delete_session(mfa_session_id)
        raise TooManyTOTPAttemptsError(
            session_attempts_remaining=0,
            global_attempts_remaining=global_remaining,
            lockout_reason="session_limit",
        )

    # Get user and verify recovery code
    async with atomic(session):
        user: User = await UsersCRUD(session).get_by_id(user_id)

        # Verify and mark recovery code as used
        try:
            await verify_recovery_code_service(session, user_id, verify_request.code)

            # Extract request metadata for security notification
            request_metadata = extract_request_metadata(request)

            # Send recovery code notifications (used + warning if needed)
            await send_recovery_code_notifications(
                session=session,
                user=user,
                used_at=datetime.now(timezone.utc),
                request_info=request_metadata,
            )

        except RecoveryCodeNotFoundError:
            # No unused codes exist - increment both counters
            session_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)
            global_count = await mfa_service.increment_global_failed_attempts(user_id)

            # Calculate remaining attempts using service methods
            global_remaining = await mfa_service.get_remaining_global_attempts(user_id)

            logger.warning(
                f"Recovery code verification failed - no unused codes user_id={user_id} "
                f"email={user.email_encrypted} failed_attempts={session_count} "
                f"global_failed_attempts={global_count}"
            )

            # Check if global lockout threshold reached
            if global_count >= settings.redis.mfa_global_lockout_attempts:
                logger.warning(
                    f"User globally locked out after max failed attempts user_id={user_id} "
                    f"email={user.email_encrypted} global_failed_attempts={global_count}"
                )
                await mfa_service.delete_session(mfa_session_id)
                raise MFAGlobalLockoutError(
                    global_attempts_remaining=0,
                )

            # Check if per-session lockout threshold reached
            if session_count is not None and session_count >= settings.redis.mfa_max_attempts:
                logger.warning(
                    f"User locked out after max failed recovery code attempts for session "
                    f"user_id={user_id} email={user.email_encrypted} failed_attempts={session_count}"
                )
                await mfa_service.delete_session(mfa_session_id)
                raise TooManyTOTPAttemptsError(
                    session_attempts_remaining=0,
                    global_attempts_remaining=global_remaining,
                    lockout_reason="session_limit",
                )

            raise

        except RecoveryCodeInvalidError:
            # Invalid code - increment both per-session and global counters
            session_count = await mfa_service.increment_failed_totp_attempts(mfa_session_id)
            global_count = await mfa_service.increment_global_failed_attempts(user_id)

            # Calculate remaining attempts using service methods
            global_remaining = await mfa_service.get_remaining_global_attempts(user_id)
            session_remaining = await mfa_service.get_remaining_session_attempts(mfa_session_id)

            logger.warning(
                f"Invalid recovery code provided user_id={user_id} email={user.email_encrypted} "
                f"failed_attempts={session_count} global_failed_attempts={global_count}"
            )

            # Check if global lockout threshold reached
            if global_count >= settings.redis.mfa_global_lockout_attempts:
                logger.warning(
                    f"User globally locked out after max failed recovery code attempts "
                    f"user_id={user_id} email={user.email_encrypted} global_failed_attempts={global_count}"
                )
                await mfa_service.delete_session(mfa_session_id)
                raise MFAGlobalLockoutError(
                    global_attempts_remaining=0,
                )

            # Check if per-session lockout threshold reached
            if session_count is not None and session_count >= settings.redis.mfa_max_attempts:
                logger.warning(
                    f"User locked out after max failed recovery code attempts for session "
                    f"user_id={user_id} email={user.email_encrypted} failed_attempts={session_count}"
                )
                await mfa_service.delete_session(mfa_session_id)
                raise TooManyTOTPAttemptsError(
                    session_attempts_remaining=0,
                    global_attempts_remaining=global_remaining,
                    lockout_reason="session_limit",
                )

            # Re-raise with metadata to inform frontend of remaining attempts
            raise RecoveryCodeInvalidError(
                metadata={
                    "session_attempts_remaining": session_remaining if session_remaining is not None else 0,
                    "global_attempts_remaining": global_remaining if global_remaining is not None else 0,
                }
            )

        # Recovery code valid - clear lockout and delete MFA session
        await mfa_service.clear_global_lockout(user_id)
        await mfa_service.delete_session(mfa_session_id)

        logger.info(
            f"MFA recovery code verification successful user_id={user_id} email={user.email_encrypted} "
            f"device_id={verify_request.device_id}"
        )

        # Step 5: Register device if device_id provided
        if verify_request.device_id:
            await UserDeviceService(session, user_id).add_device(
                UserDeviceCreate(
                    device_id=verify_request.device_id,
                    os=AppInfoOS(name=os_name, version=os_version) if os_name and os_version else None,
                    app_version=app_version,
                )
            )

        # Step 6: Issue refresh and access tokens
        rjti = str(uuid.uuid4())
        refresh_token = AuthenticationService.create_refresh_token({JWTClaim.sub: str(user_id), JWTClaim.jti: rjti})

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(user_id),
                JWTClaim.rjti: rjti,
            }
        )

    # Step 7: Return response
    token = Token(access_token=access_token, refresh_token=refresh_token)
    public_user = PublicUser.from_user(user)

    return Response(
        result=UserLogin(
            token=token,
            user=public_user,
        )
    )


async def refresh_access_token(
    schema: RefreshAccessTokenRequest = Body(...),
    session=Depends(get_session),
) -> Response[Token]:
    """Refresh access token."""
    async with atomic(session):
        try:
            regenerate_refresh_token = False
            try:
                payload = jwt.decode(
                    schema.refresh_token,
                    settings.authentication.refresh_token.secret_key,
                    algorithms=[settings.authentication.algorithm],
                )
            except jwt.PyJWTError:
                # check transition key
                transition_key = settings.authentication.refresh_token.transition_key
                transition_expire_date = settings.authentication.refresh_token.transition_expire_date
                today = datetime.now(timezone.utc).date()

                if not (transition_key and transition_expire_date and transition_expire_date > today):
                    raise
                payload = jwt.decode(
                    schema.refresh_token,
                    str(transition_key),
                    algorithms=[settings.authentication.algorithm],
                )
                regenerate_refresh_token = True

            token_data = TokenPayload(**payload)

        except (jwt.PyJWTError, ValidationError) as e:
            raise InvalidRefreshToken() from e

        # Check if the token is in the blacklist
        revoked = await AuthenticationService(session).is_revoked(InternalToken(payload=token_data))
        if revoked:
            raise AuthenticationError

        rjti = token_data.jti
        user_id = token_data.sub
        refresh_token = schema.refresh_token
        if regenerate_refresh_token:
            # blacklist current refresh token
            await AuthenticationService(session).revoke_token(InternalToken(payload=token_data), TokenPurpose.REFRESH)

            rjti = str(uuid.uuid4())
            refresh_token = AuthenticationService.create_refresh_token(
                {JWTClaim.sub: str(user_id), JWTClaim.jti: rjti, JWTClaim.exp: token_data.exp}
            )

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(user_id),
                JWTClaim.rjti: rjti,
            }
        )

    return Response(result=Token(access_token=access_token, refresh_token=refresh_token))


async def delete_access_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token()),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> EmptyResponse:
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(token, TokenPurpose.ACCESS)
    async with atomic(session):
        if schema and schema.device_id:
            await UserDeviceService(session, user.id).remove_device(schema.device_id)
    return EmptyResponse()


async def delete_refresh_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token(TokenPurpose.REFRESH)),
    session=Depends(get_session),
) -> EmptyResponse:
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(token, TokenPurpose.REFRESH)
    if schema and schema.device_id:
        async with atomic(session):
            await UserDeviceService(session, token.payload.sub).remove_device(schema.device_id)
    return EmptyResponse()
