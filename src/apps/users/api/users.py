from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.crud import UsersCRUD
from apps.users.domain import PublicUser, User, UserUpdate


async def get_user(
    user: User = Depends(get_current_user),
) -> Response[PublicUser]:
    # Get public representation of the authenticated user
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def update_user(
    user: User = Depends(get_current_user),
    user_update_schema: UserUpdate = Body(...),
) -> Response[PublicUser]:
    updated_user: User = await UsersCRUD().update(user, user_update_schema)

    # Create public representation of the internal user
    public_user = PublicUser(**updated_user.dict())

    return Response(result=public_user)


async def delete_user(user: User = Depends(get_current_user)) -> None:
    await UsersCRUD().delete(user)
    raise NotContentError
