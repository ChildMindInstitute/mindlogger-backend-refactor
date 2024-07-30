import uuid
from datetime import datetime

from fastapi import Body, Depends
from jose import JWTError, jwt
from pydantic import ValidationError

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
from apps.authentication.errors import AuthenticationError, InvalidCredentials, InvalidRefreshToken
from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.response import EmptyResponse
from apps.users import UsersCRUD
from apps.users.domain import PublicUser, User, UserDeviceCreate
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
            user: User = await AuthenticationService(session).authenticate_user(user_login_schema)
            if user_login_schema.device_id:
                await UserDeviceService(session, user.id).add_device(
                    UserDeviceCreate(device_id=user_login_schema.device_id)
                )
        except UserNotFound:
            raise InvalidCredentials(email=user_login_schema.email)

        if user.email_encrypted != user_login_schema.email:
            user = await UsersCRUD(session).update_encrypted_email(user, user_login_schema.email)

    rjti = str(uuid.uuid4())
    refresh_token = AuthenticationService.create_refresh_token({JWTClaim.sub: str(user.id), JWTClaim.jti: rjti})

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
            regenerate_refresh_token = False
            try:
                payload = jwt.decode(
                    schema.refresh_token,
                    settings.authentication.refresh_token.secret_key,
                    algorithms=[settings.authentication.algorithm],
                )
            except JWTError:
                # check transition key
                transition_key = settings.authentication.refresh_token.transition_key
                transition_expire_date = settings.authentication.refresh_token.transition_expire_date

                if not (
                    transition_key and transition_expire_date and transition_expire_date > datetime.utcnow().date()
                ):
                    raise
                payload = jwt.decode(
                    schema.refresh_token,
                    transition_key,
                    algorithms=[settings.authentication.algorithm],
                )
                regenerate_refresh_token = True

            token_data = TokenPayload(**payload)

        except (JWTError, ValidationError) as e:
            raise InvalidRefreshToken() from e

        # Check if the token is in the blacklist
        revoked = await AuthenticationService(session).is_revoked(InternalToken(payload=token_data))
        if revoked:
            raise AuthenticationError

        rjti = token_data.jti
        user_id = token_data.sub
        refresh_token = schema.refresh_token
        if regenerate_refresh_token:
            # blacklist current refresh token
            await AuthenticationService(session).revoke_token(InternalToken(payload=token_data), TokenPurpose.REFRESH)

            rjti = str(uuid.uuid4())
            refresh_token = AuthenticationService.create_refresh_token(
                {JWTClaim.sub: str(user_id), JWTClaim.jti: rjti, JWTClaim.exp: token_data.exp}
            )

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(user_id),
                JWTClaim.rjti: rjti,
            }
        )

    return Response(result=Token(access_token=access_token, refresh_token=refresh_token))


async def delete_access_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token()),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> EmptyResponse:
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(token, TokenPurpose.ACCESS)
    async with atomic(session):
        if schema and schema.device_id:
            await UserDeviceService(session, user.id).remove_device(schema.device_id)
    return EmptyResponse()


async def delete_refresh_token(
    schema: UserLogoutRequest | None = Body(default=None),
    token: InternalToken = Depends(get_current_token(TokenPurpose.REFRESH)),
    session=Depends(get_session),
) -> EmptyResponse:
    """Add token to the blacklist."""
    async with atomic(session):
        await AuthenticationService(session).revoke_token(token, TokenPurpose.REFRESH)
    if schema and schema.device_id:
        async with atomic(session):
            await UserDeviceService(session, token.payload.sub).remove_device(schema.device_id)
    return EmptyResponse()
