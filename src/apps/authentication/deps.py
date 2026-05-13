import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.websockets import WebSocket
from pydantic import ValidationError
from starlette.requests import Request

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken, JWTClaim, TokenPayload, TokenPurpose
from apps.authentication.errors import SessionTokenInvalidError
from apps.authentication.services import AuthenticationService
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from apps.users.errors import UserIsDeletedError, UserNotFound
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

oauth2_oauth = OAuth2PasswordBearer(tokenUrl="/auth/openapi", scheme_name="Bearer")


def _expired_token_sub(token: str, key: str) -> uuid.UUID | None:
    """Extract expired token subject. For audit logging only."""
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.authentication.algorithm],
            options={"verify_exp": False},
        )
        return TokenPayload(**payload).sub
    except (jwt.PyJWTError, ValidationError):
        return None


async def get_current_user_for_ws(websocket: WebSocket, session=Depends(get_session)):
    authorization = websocket.headers.get("sec-websocket-protocol")
    try:
        if not authorization:
            raise ValueError
        scheme, token = authorization.split("|")
        if scheme.lower() != settings.authentication.token_type.lower():
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with atomic(session):
        key = settings.authentication.access_token.secret_key
        try:
            payload = jwt.decode(token, key, algorithms=[settings.authentication.algorithm])
            token_data = TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise SessionTokenInvalidError(user_id=_expired_token_sub(token, key))
        except (jwt.PyJWTError, ValidationError):
            raise SessionTokenInvalidError()

        # Check if the token is in the blacklist
        revoked = await AuthenticationService(session).is_revoked(InternalToken(payload=token_data, raw_token=token))
        if revoked:
            raise SessionTokenInvalidError(user_id=token_data.sub)

        try:
            user = await UsersCRUD(session).get_by_id(id_=token_data.sub)
        except (UserNotFound, UserIsDeletedError):
            raise SessionTokenInvalidError(user_id=token_data.sub)

    return user


def get_current_token(type_: TokenPurpose = TokenPurpose.ACCESS):
    async def _get_current_token(
        token: str = Depends(oauth2_oauth),
    ) -> InternalToken:
        key = settings.authentication.access_token.secret_key
        if type_ == TokenPurpose.REFRESH:
            key = settings.authentication.refresh_token.secret_key
        try:
            payload = jwt.decode(token, key, algorithms=[settings.authentication.algorithm])
            token_payload = TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise SessionTokenInvalidError(user_id=_expired_token_sub(token, key))
        except (jwt.PyJWTError, ValidationError):
            raise SessionTokenInvalidError()

        return InternalToken(payload=token_payload, raw_token=token)

    return _get_current_token


async def get_current_user(
    token: InternalToken = Depends(get_current_token()),
    session=Depends(get_session),
) -> User:
    async with atomic(session):
        # Check if the token is in the blacklist
        revoked = await AuthenticationService(session).is_revoked(token)
        if revoked:
            raise SessionTokenInvalidError(user_id=token.payload.sub)

        try:
            user = await UsersCRUD(session).get_by_id(id_=token.payload.sub)
        except (UserNotFound, UserIsDeletedError):
            raise SessionTokenInvalidError(user_id=token.payload.sub)
        await AuthenticationService(session).update_last_seen_at(user)

    return user


async def get_optional_current_user(request: Request, session=Depends(get_session)) -> User | None:
    try:
        user = await get_current_user(await get_current_token()(await oauth2_oauth(request)), session)
        return user
    except Exception:
        return None


async def openapi_auth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session),
) -> dict[str, str]:
    async with atomic(session):
        user_login_schema = UserLoginRequest(email=form_data.username, password=form_data.password)
        user: User = await AuthenticationService(session).authenticate_user(user_login_schema)
        access_token = AuthenticationService.create_access_token({JWTClaim.sub: str(user.id)})

    return {
        "access_token": access_token,
        "token_type": settings.authentication.token_type,
    }
