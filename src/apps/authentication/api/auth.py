from fastapi import Body, Depends

from apps.authentication.deps import get_current_token
from apps.authentication.domain import InternalToken, Token
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
    UserCreate,
    UserLoginRequest,
    UserSignUpRequest,
)
from apps.users.errors import UserNotFound, UsersError


async def create_user(
    user_create_schema: UserSignUpRequest = Body(...),
) -> Response[PublicUser]:
    try:
        await UsersCRUD().get_by_email(email=user_create_schema.email)
        raise UsersError("User already exist")
    except UserNotFound:
        user_in_db = UserCreate(
            email=user_create_schema.email,
            full_name=user_create_schema.full_name,
            hashed_password=AuthenticationService.get_password_hash(
                user_create_schema.password
            ),
        )
        user, _ = await UsersCRUD().save_user(schema=user_in_db)

    # Create public user model in order to avoid password sharing
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def get_access_token(
    user_login_schema: UserLoginRequest = Body(...),
) -> Response[Token]:
    user: User = await AuthenticationService.authenticate_user(
        user_login_schema
    )

    access_token = AuthenticationService.create_access_token(
        {"sub": user.email}
    )

    return Response(result=Token(access_token=access_token))


async def access_token_delete(
    token: InternalToken = Depends(get_current_token),
):
    await AuthenticationService.add_access_token_to_blacklist(token)
    raise NotContentError
