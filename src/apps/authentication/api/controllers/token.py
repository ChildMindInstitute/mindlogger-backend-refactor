from fastapi import APIRouter, Body, Depends
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
from apps.users.domain import User, UserLoginRequest
from apps.users.errors import UsersError
from apps.users.services import UsersCRUD
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def authenticate_user(user_login_schema: UserLoginRequest = Body(...)):
    user: User = await UsersCRUD().get_by_email(email=user_login_schema.email)

    if not AuthenticationService.verify_password(
        user_login_schema.password, user.hashed_password
    ):
        raise BadCredentials("Invalid password")

    return user


@router.post("/access-token", tags=["Authentication"])
async def get_access_token(
    user_login_schema: UserLoginRequest = Body(...),
) -> Response[Token]:
    user: User = await authenticate_user(user_login_schema)

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


# @router.post("/signout", tags=["Authentication"])
async def access_token_delete(user: User = Depends(get_current_user)) -> None:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        instance: Token = await TokensCRUD().get_by_email(email=user.email)
        await TokensCRUD().delete_by_id(instance.id)
    except UsersError:
        raise access_token_not_correct


# @router.post("/refresh-access-token", tags=["Authentication"])
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
