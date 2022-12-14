from contextlib import suppress
from datetime import datetime

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from apps.authentication.domain.token import (
    InternalToken,
    TokenInfo,
    TokenPayload,
)
from apps.authentication.errors import AuthenticationError
from apps.authentication.services import AuthenticationService
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from apps.users.errors import UserNotFound
from config import settings
from infrastructure.cache import CacheNotFound

oauth2_oauth = OAuth2PasswordBearer(
    tokenUrl="/refresh-access-token", scheme_name="Bearer"
)


async def get_current_user(token: str = Depends(oauth2_oauth)) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.authentication.access_token.secret_key,
            algorithms=[settings.authentication.algorithm],
        )
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise AuthenticationError()
    except (JWTError, ValidationError):
        raise AuthenticationError()

    if not (user := await UsersCRUD().get_by_id(id_=token_data.sub)):
        raise UserNotFound()

    # Check if the token is in the blacklist
    with suppress(CacheNotFound):
        cache_entries: list[
            TokenInfo
        ] = await AuthenticationService().fetch_all_tokens(user.email)

        for entry in cache_entries:
            if entry.raw_token == token:
                raise AuthenticationError()

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
            raise AuthenticationError()
    except (JWTError, ValidationError):
        raise AuthenticationError()

    return InternalToken(payload=token_payload, raw_token=token)
