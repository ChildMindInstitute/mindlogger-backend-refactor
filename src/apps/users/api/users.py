from typing import Any

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
)


async def get_user_me(
    user: User = Depends(get_current_user)
) -> Response[PublicUser]:
    public_user = PublicUser(**user.dict())
    return Response(result=public_user)


async def update_user_me(
    user: User = Depends(get_current_user),
    payloads: list[dict[str, Any]] = Body(...),
) -> Response[PublicUser]:
    await UsersCRUD().update(lookup=("id", user.id), payloads=payloads)
    user: User = await UsersCRUD().get_by_id(id_=user.id)
    public_user = PublicUser(**user.dict())
    return Response(result=public_user)


async def delete_user_me(
    user: User = Depends(get_current_user)
) -> None:
    await UsersCRUD().update(lookup=("id", user.id), payloads=[{"is_deleted": True}])
    raise NotContentError
