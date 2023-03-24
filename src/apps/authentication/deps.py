from contextlib import suppress
from datetime import datetime

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr, ValidationError

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import (
    InternalToken,
    TokenPayload,
)
from apps.authentication.errors import AuthenticationError
from apps.authentication.services import AuthenticationService
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from apps.users.errors import UserNotFound
from config import settings
from infrastructure.cache import CacheNotFound
from infrastructure.database import atomic, session_manager

oauth2_oauth = OAuth2PasswordBearer(
    tokenUrl="/auth/openapi", scheme_name="Bearer"
)


async def get_current_user(
    token: str = Depends(oauth2_oauth),
    session=Depends(session_manager.get_session),
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

        if not (
            user := await UsersCRUD(session).get_by_id(id_=token_data.sub)
        ):
            raise UserNotFound()

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
    session=Depends(session_manager.get_session),
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
