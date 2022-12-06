from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from apps.authentication.errors import BadCredentials
from apps.users.crud import UsersCRUD
from apps.users.domain import User, UserLoginRequest
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.access_token_expire_minutes
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.refresh_token_expire_minutes
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.refresh_secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    async def authenticate_user(user_login_schema: UserLoginRequest):
        user: User = await UsersCRUD().get_by_email(
            email=user_login_schema.email
        )

        if not AuthenticationService.verify_password(
            user_login_schema.password, user.hashed_password
        ):
            raise BadCredentials("Invalid password")

        return user
