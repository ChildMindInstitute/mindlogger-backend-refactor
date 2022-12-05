from fastapi import Body, Depends
from jose import JWTError, jwt

from apps.authentication.deps import get_current_user
from apps.authentication.domain import (
    RefreshAccessTokenRequest,
    Token,
    TokenCreate,
    TokenRefresh,
)
from apps.authentication.errors import BadCredentials
from apps.authentication.services.crud import TokensCRUD
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.domain import (
    PublicUser,
    User,
    UserCreate,
    UserLoginRequest,
    UserSignUpRequest,
)
from apps.users.errors import UserNotFound, UsersError
from apps.users.services import UsersCRUD
from config import settings


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
        data={"sub": user.email}
    )
    refresh_token = AuthenticationService.create_refresh_token(
        data={"sub": user.email}
    )

    await TokensCRUD().delete_by_email(user.email)

    token, _ = await TokensCRUD().save(
        TokenCreate(
            email=user_login_schema.email,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )

    return Response(result=token)


async def access_token_delete(user: User = Depends(get_current_user)):
    access_token_not_correct: Exception = BadCredentials(
        message="Access token is not correct"
    )

    try:
        instance: Token = await TokensCRUD().get_by_email(email=user.email)
        await TokensCRUD().delete_by_id(instance.id)
        raise NotContentError
    except UsersError:
        raise access_token_not_correct


async def refresh_access_token(
    refresh_access_token_schema: RefreshAccessTokenRequest = Body(...),
) -> Response[TokenRefresh]:
    """Refresh access token."""

    refresh_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )

    try:
        payload = jwt.decode(
            refresh_access_token_schema.refresh_token,
            settings.authentication.refresh_secret_key,
            algorithms=[settings.authentication.algorithm],
        )

        if not (email := payload.get("sub")):
            raise refresh_token_not_correct

    except JWTError:
        raise refresh_token_not_correct

    instance: Token = await TokensCRUD().get_by_email(email=email)
    token: Token = await TokensCRUD().refresh_access_token(instance.id)
    token_refresh = TokenRefresh(**token.dict())

    return Response(result=token_refresh)
