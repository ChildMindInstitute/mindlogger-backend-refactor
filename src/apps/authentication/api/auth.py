import uuid
from datetime import datetime

from fastapi import Body, Depends
from jose import JWTError, jwt
from pydantic import ValidationError

from apps.authentication.api.auth_utils import auth_user
from apps.authentication.deps import get_current_token, get_current_user
from apps.authentication.domain.login import UserLogin, UserLoginRequest
from apps.authentication.domain.logout import UserLogoutRequest
from apps.authentication.domain.token import (
    InternalToken,
    JWTClaim,
    RefreshAccessTokenRequest,
    Token,
    TokenPayload,
    TokenPurpose,
)
from apps.authentication.errors import AuthenticationError, InvalidRefreshToken
from apps.authentication.services.security import AuthenticationService
from apps.logs.user_activity_log import user_activity_login_log
from apps.shared.domain.response import Response
from apps.shared.response import EmptyResponse
from apps.users import UsersCRUD
from apps.users.domain import PublicUser, User
from apps.users.services.user_device import UserDeviceService
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def get_token(
    user_login_schema: UserLoginRequest = Body(...),
    session=Depends(get_session),
    user=Depends(auth_user),
    user_activity_log=Depends(user_activity_login_log),
) -> Response[UserLogin]:
    """Generate the JWT access token."""
    async with atomic(session):
        if user_login_schema.device_id:
            await UserDeviceService(session, user.id).add_device(
                user_login_schema.device_id
            )
        if user.email_encrypted != user_login_schema.email:
            user = await UsersCRUD(session).update_encrypted_email(
                user, user_login_schema.email
            )

    rjti = str(uuid.uuid4())
    refresh_token = AuthenticationService.create_refresh_token(
        {JWTClaim.sub: str(user.id), JWTClaim.jti: rjti}
    )

    access_token = AuthenticationService.create_access_token(
        {
            JWTClaim.sub: str(user.id),
            JWTClaim.rjti: rjti,
        }
    )

    token = Token(access_token=access_token, refresh_token=refresh_token)
    public_user = PublicUser.from_user(user)

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
        try:
            payload = jwt.decode(
                schema.refresh_token,
                settings.authentication.refresh_token.secret_key,
                algorithms=[settings.authentication.algorithm],
            )
            token_data = TokenPayload(**payload)

            if datetime.utcfromtimestamp(token_data.exp) < datetime.utcnow():
                raise AuthenticationError

            if not (user_id := payload[JWTClaim.sub]):
                raise InvalidRefreshToken()

        except (JWTError, ValidationError) as e:
            raise InvalidRefreshToken() from e

        # Check if the token is in the blacklist
        revoked = await AuthenticationService(session).is_revoked(
            InternalToken(payload=token_data)
        )
        if revoked:
            raise AuthenticationError

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(user_id),
                JWTClaim.rjti: token_data.jti,
            }
        )

    return Response(
        result=Token(
            access_token=access_token, refresh_token=schema.refresh_token
        )
    )


async def delete_access_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token()),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(
            token, TokenPurpose.ACCESS
        )
    async with atomic(session):
        if schema and schema.device_id:
            await UserDeviceService(session, user.id).remove_device(
                schema.device_id
            )
    return EmptyResponse()


async def delete_refresh_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token(TokenPurpose.REFRESH)),
    session=Depends(get_session),
):
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(
            token, TokenPurpose.REFRESH
        )
    if schema and schema.device_id:
        async with atomic(session):
            await UserDeviceService(session, token.payload.sub).remove_device(
                schema.device_id
            )
    return EmptyResponse()
