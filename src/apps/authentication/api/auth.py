from fastapi import Body, Depends
from jose import JWTError, jwt

from apps.authentication.deps import get_current_token, get_current_user
from apps.authentication.domain.login import UserLogin, UserLoginRequest
from apps.authentication.domain.logout import UserLogoutRequest
from apps.authentication.domain.token import (
    InternalToken,
    RefreshAccessTokenRequest,
    Token,
)
from apps.authentication.errors import BadCredentials
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.domain import PublicUser, User
from apps.users.errors import UserNotFound
from apps.users.services.user_device import UserDeviceService
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def get_token(
    user_login_schema: UserLoginRequest = Body(...),
    session=Depends(get_session),
) -> Response[UserLogin]:
    """Generate the JWT access token."""
    async with atomic(session):
        try:
            user: User = await AuthenticationService(
                session
            ).authenticate_user(user_login_schema)
            if user_login_schema.device_id:
                await UserDeviceService(session, user.id).add_device(
                    user_login_schema.device_id
                )
        except UserNotFound:
            raise UserNotFound(
                message=(
                    "That email is not associated with a MindLogger account."
                )
            )
    access_token = AuthenticationService.create_access_token(
        {"sub": str(user.id)}
    )

    refresh_token = AuthenticationService.create_refresh_token(
        {"sub": str(user.id)}
    )

    token = Token(access_token=access_token, refresh_token=refresh_token)
    public_user = PublicUser(**user.dict())

    return Response(
        result=UserLogin(
            token=token,
            user=public_user,
        )
    )


async def refresh_access_token(
    schema: RefreshAccessTokenRequest = Body(...),
    session=Depends(get_session),
) -> Response[Token]:
    """Refresh access token."""
    async with atomic(session):
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

        access_token = AuthenticationService(session).create_access_token(
            {"sub": str(user_id)}
        )

    return Response(
        result=Token(
            access_token=access_token, refresh_token=schema.refresh_token
        )
    )


async def delete_access_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).add_access_token_to_blacklist(
            token
        )
        if schema and schema.device_id:
            await UserDeviceService(session, user.id).remove_device(
                schema.device_id
            )
    return ""
