from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
    UserCreate,
    UserCreateRequest,
    UserUpdateRequest,
)


async def user_create(
    user_create_schema: UserCreateRequest = Body(...),
) -> Response[PublicUser]:

    user_create = UserCreate(
        email=user_create_schema.email,
        full_name=user_create_schema.full_name,
        hashed_password=AuthenticationService.get_password_hash(
            user_create_schema.password
        ),
    )
    user, _ = await UsersCRUD().save(schema=user_create)

    # Create public user model in order to avoid password sharing
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def user_retrieve(
    user: User = Depends(get_current_user),
) -> Response[PublicUser]:
    # Get public representation of the authenticated user
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def user_update(
    user: User = Depends(get_current_user),
    user_update_schema: UserUpdateRequest = Body(...),
) -> Response[PublicUser]:
    updated_user: User = await UsersCRUD().update(user, user_update_schema)

    # Create public representation of the internal user
    public_user = PublicUser(**updated_user.dict())

    return Response(result=public_user)


async def user_delete(user: User = Depends(get_current_user)) -> None:
    await UsersCRUD().delete(user)
