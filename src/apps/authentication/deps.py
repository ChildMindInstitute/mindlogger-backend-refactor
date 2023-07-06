from contextlib import suppress
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.websockets import WebSocket
from jose import JWTError, jwt
from pydantic import EmailStr, ValidationError

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken, TokenPayload
from apps.authentication.errors import AuthenticationError
from apps.authentication.services import AuthenticationService
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from config import settings
from infrastructure.cache import CacheNotFound
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

oauth2_oauth = OAuth2PasswordBearer(
    tokenUrl="/auth/openapi", scheme_name="Bearer"
)


async def get_current_user_for_ws(
    websocket: WebSocket, session=Depends(get_session)
):
    authorization = websocket.headers.get("sec-websocket-protocol")
    if authorization:
        authorization = " ".join(authorization.split("_"))
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with atomic(session):
        try:
            payload = jwt.decode(
                token,
                settings.authentication.access_token.secret_key,
                algorithms=[settings.authentication.algorithm],
            )
            token_data = TokenPayload(**payload)

            if datetime.fromtimestamp(token_data.exp) < datetime.now():
                raise AuthenticationError
        except (JWTError, ValidationError):
            raise AuthenticationError

        user = await UsersCRUD(session).get_by_id(id_=token_data.sub)
        await UsersCRUD(session).update_last_seen_by_id(token_data.sub)

        # Check if the token is in the blacklist
        with suppress(CacheNotFound):
            cache_entries = await AuthenticationService(
                session
            ).fetch_all_tokens(user.email)

            for entry in cache_entries:
                if entry.raw_token == token:
                    raise AuthenticationError

    return user


async def get_current_user(
    token: str = Depends(oauth2_oauth),
    session=Depends(get_session),
) -> User:
    async with atomic(session):
        try:
            payload = jwt.decode(
                token,
                settings.authentication.access_token.secret_key,
                algorithms=[settings.authentication.algorithm],
            )
            token_data = TokenPayload(**payload)

            if datetime.fromtimestamp(token_data.exp) < datetime.now():
                raise AuthenticationError
        except (JWTError, ValidationError):
            raise AuthenticationError

        user = await UsersCRUD(session).get_by_id(id_=token_data.sub)
        await UsersCRUD(session).update_last_seen_by_id(token_data.sub)

        # Check if the token is in the blacklist
        with suppress(CacheNotFound):
            cache_entries = await AuthenticationService(
                session
            ).fetch_all_tokens(user.email)

            for entry in cache_entries:
                if entry.raw_token == token:
                    raise AuthenticationError

    return user


async def get_current_token(
    token: str = Depends(oauth2_oauth),
) -> InternalToken:
    try:
        payload = jwt.decode(
            token,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )

        token_payload = TokenPayload(**payload)

        if datetime.fromtimestamp(token_payload.exp) < datetime.now():
            raise AuthenticationError
    except (JWTError, ValidationError):
        raise AuthenticationError

    return InternalToken(payload=token_payload, raw_token=token)


async def openapi_auth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session),
):
    async with atomic(session):
        user_login_schema = UserLoginRequest(
            email=EmailStr(form_data.username), password=form_data.password
        )
        user: User = await AuthenticationService(session).authenticate_user(
            user_login_schema
        )
        if not user:
            raise AuthenticationError

        user = await AuthenticationService(session).authenticate_user(
            user_login_schema
        )
        access_token = AuthenticationService.create_access_token(
            {"sub": str(user.id)}
        )

    return {
        "access_token": access_token,
        "token_type": settings.authentication.token_type,
    }
