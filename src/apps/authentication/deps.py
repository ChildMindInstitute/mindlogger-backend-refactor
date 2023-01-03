from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from apps.authentication.domain import InternalToken, TokenPayload, TokenInfo
from apps.authentication.services import AuthenticationService
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from config import settings

oauth2_oauth = OAuth2PasswordBearer(
    tokenUrl="/refresh-access-token", scheme_name="Bearer"
)


async def get_current_user(token: str = Depends(oauth2_oauth)) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.authentication.secret_keys.authentication,
            algorithms=[settings.authentication.algorithm],
        )
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User = await UsersCRUD().get_by_id(id_=token_data.sub)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    # Checking if the token is blacklisted.
    cache_entries: list[TokenInfo] = await AuthenticationService().fetch_all(user.email)

    if cache_entries:
        for entry in cache_entries:
            if entry.raw_token == token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is invalid",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    return user


async def get_current_token(
    token: str = Depends(oauth2_oauth),
) -> InternalToken:
    try:
        payload = jwt.decode(
            token,
            settings.authentication.secret_keys.authentication,
            algorithms=[settings.authentication.algorithm],
        )

        token_payload = TokenPayload(**payload)

        if datetime.fromtimestamp(token_payload.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return InternalToken(payload=token_payload, raw_token=token)
