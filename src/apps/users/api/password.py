from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    ChangePasswordRequest,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryInfo,
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserChangePassword,
)
from apps.users.services import PasswordRecoveryService


async def password_update(
    user: User = Depends(get_current_user),
    schema: ChangePasswordRequest = Body(...),
) -> Response[PublicUser]:
    """General endpoint for update password
    for signin.
    """
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
) -> Response[PasswordRecoveryInfo]:
    """General endpoint for sending password recovery email
    and stored info in Redis.
    """

    # Send the password recovery the internal password recovery service
    password_recovery_info: PasswordRecoveryInfo = (
        await PasswordRecoveryService().send_password_recovery(schema)
    )

    return Response[PasswordRecoveryInfo](result=password_recovery_info)


async def password_recovery_approve(
    schema: PasswordRecoveryApproveRequest = Body(...),
):
    pass
