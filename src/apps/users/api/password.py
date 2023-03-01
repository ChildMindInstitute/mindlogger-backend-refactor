from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    ChangePasswordRequest,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserChangePassword,
)
from apps.users.errors import UserNotFound
from apps.users.services import PasswordRecoveryService


async def password_update(
    user: User = Depends(get_current_user),
    schema: ChangePasswordRequest = Body(...),
) -> Response[PublicUser]:
    """General endpoint for update password for signin."""

    AuthenticationService.verify_password(
        schema.prev_password,
        user.hashed_password,
    )

    password_hash: str = AuthenticationService.get_password_hash(
        schema.password
    )
    password = UserChangePassword(hashed_password=password_hash)

    updated_user: User = await UsersCRUD().change_password(user, password)

    # Create public representation of the internal user
    public_user = PublicUser(**updated_user.dict())

    return Response[PublicUser](result=public_user)


async def password_recovery(
    schema: PasswordRecoveryRequest = Body(...),
) -> Response[PublicUser]:
    """General endpoint for sending password recovery email
    and stored info in Redis.
    """
    # Send the password recovery the internal password recovery service
    try:
        public_user: PublicUser = (
            await PasswordRecoveryService().send_password_recovery(schema)
        )
    except UserNotFound:
        raise UserNotFound(
            message="That email is not associated with a MindLogger account"
        )

    return Response[PublicUser](result=public_user)


async def password_recovery_approve(
    schema: PasswordRecoveryApproveRequest = Body(...),
) -> Response[PublicUser]:
    """General endpoint to approve the password recovery."""

    # Approve the password recovery
    # NOTE: also check if the data exists and tokens are not expired
    public_user: PublicUser = await PasswordRecoveryService().approve(schema)

    return Response[PublicUser](result=public_user)
