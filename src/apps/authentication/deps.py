from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from apps.users.services import UsersCRUD
from config import settings

from jose import jwt, JWTError
from pydantic import ValidationError
from apps.users.domain import User
from apps.authentication.domain import TokenPayload, RefreshAcceessTokenRequest

oauth2_oauth = OAuth2PasswordBearer(
    tokenUrl="/refresh-access-token",
    scheme_name="JWT"
)


async def get_current_user(token: RefreshAcceessTokenRequest = Depends(oauth2_oauth)) -> User:
    try:
        payload = jwt.decode(
            token, settings.authentication.secret_key, algorithms=[settings.authentication.algorithm]
        )
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except(JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User = await UsersCRUD().get_by_email(email=token_data.sub)
    # user: Union[dict[str, Any], None] = db.get(token_data.email, None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    return user
