from fastapi import Body, Depends
from jose import JWTError, jwt

from apps.authentication.deps import get_current_token, get_current_user
from apps.authentication.domain.token import (
    InternalToken,
    RefreshAccessTokenRequest,
    Token,
)
from apps.authentication.errors import BadCredentials
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.errors import NotContentError
from apps.users.domain import DeviceIdRequest, User, UserLoginRequest
from config import settings


async def get_token(
    user_login_schema: UserLoginRequest = Body(...),
) -> Response[Token]:
    """Generate the JWT access token."""

    user: User = await AuthenticationService.authenticate_user(
        user_login_schema
    )

    access_token = AuthenticationService.create_access_token(
        {"sub": str(user.id)}
    )

    refresh_token = AuthenticationService.create_refresh_token(
        {"sub": str(user.id)}
    )

    return Response(
        result=Token(access_token=access_token, refresh_token=refresh_token)
    )


async def refresh_access_token(
    schema: RefreshAccessTokenRequest = Body(...),
) -> Response[Token]:
    """Refresh access token."""

    refresh_token_not_correct = BadCredentials(
        message="Refresh token is invalid"
    )

    try:
        payload = jwt.decode(
            schema.refresh_token,
            settings.authentication.refresh_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )

        if not (user_id := payload.get("sub")):
            raise refresh_token_not_correct

    except JWTError:
        raise BadCredentials(message="Refresh token is invalid")

    access_token = AuthenticationService.create_access_token(
        {"sub": str(user_id)}
    )

    return Response(
        result=Token(
            access_token=access_token, refresh_token=schema.refresh_token
        )
    )


async def delete_access_token(
    token: InternalToken = Depends(get_current_token),
    _: User = Depends(get_current_user),
    schema: DeviceIdRequest = Body(...),
):
    """Add token to the blacklist."""

    await AuthenticationService.add_access_token_to_blacklist(token)
    raise NotContentError
