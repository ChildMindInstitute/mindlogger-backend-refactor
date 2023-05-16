from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    ChangePasswordRequest,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryHealthCheckRequest,
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserChangePassword,
)
from apps.users.errors import EmailAddressError, UserNotFound
from apps.users.services import PasswordRecoveryCache, PasswordRecoveryService
from infrastructure.cache import (
    CacheNotFound,
    PasswordRecoveryHealthCheckNotValid,
)
from infrastructure.database import atomic, session_manager


async def password_update(
    user: User = Depends(get_current_user),
    schema: ChangePasswordRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicUser]:
    """General endpoint for update password for signin."""
    async with atomic(session):
        AuthenticationService.verify_password(
            schema.prev_password,
            user.hashed_password,
        )

        password_hash: str = AuthenticationService.get_password_hash(
            schema.password
        )
        password = UserChangePassword(hashed_password=password_hash)

        updated_user: User = await UsersCRUD(session).change_password(
            user, password
        )

        # Create public representation of the internal user
        public_user = PublicUser(**updated_user.dict())

    return Response[PublicUser](result=public_user)


async def password_recovery(
    schema: PasswordRecoveryRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicUser]:
    """General endpoint for sending password recovery email
    and stored info in Redis.
    """
    # Send the password recovery the internal password recovery service
    async with atomic(session):
        try:
            public_user: PublicUser = await PasswordRecoveryService(
                session
            ).send_password_recovery(schema)
        except UserNotFound:
            raise EmailAddressError(email=schema.email)

    return Response[PublicUser](result=public_user)


async def password_recovery_approve(
    schema: PasswordRecoveryApproveRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicUser]:
    """General endpoint to approve the password recovery."""

    # Approve the password recovery
    # NOTE: also check if the data exists and tokens are not expired
    async with atomic(session):
        public_user: PublicUser = await PasswordRecoveryService(
            session
        ).approve(schema)

    return Response[PublicUser](result=public_user)


async def password_recovery_healthcheck(
    schema: PasswordRecoveryHealthCheckRequest = Body(...),
):
    """General endpoint to get the password recovery healthcheck."""

    try:
        await PasswordRecoveryCache().get(schema.email, schema.key)
    except CacheNotFound:
        raise PasswordRecoveryHealthCheckNotValid()
