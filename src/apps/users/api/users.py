from datetime import datetime, timezone

from fastapi import Body, Depends
from fastapi.responses import Response as FastAPIResponse

from apps.authentication.deps import get_current_user
from apps.authentication.domain.recovery_code.public import RecoveryCodesListResponse
from apps.authentication.services.recovery_codes import (
    format_recovery_codes_text,
    generate_recovery_codes,
    get_recovery_codes,
)
from apps.shared.domain.response import Response
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
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
from apps.users.errors import InvalidTOTPCodeError, MFANotEnabledError, RecoveryCodesNotFoundError
from apps.users.services.totp import totp_service
from apps.users.services.user import UserService
from apps.users.services.user_device import UserDeviceService
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database.core import atomic
from infrastructure.database.deps import get_session


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
        codes = None
        if fresh_user.recovery_codes_generated_at is None:
            codes = await generate_recovery_codes(session, fresh_user.id)

    result = TOTPVerifyResponse(
        message="TOTP MFA has been successfully enabled for your account.",
        mfa_enabled=True,
        recovery_codes=codes,
    )

    return Response(result=result)


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

    # Return as downloadable text file
    return FastAPIResponse(
        content=text_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
