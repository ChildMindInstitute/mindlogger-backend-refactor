from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from apps.authentication.domain import InternalToken
from apps.authentication.errors import BadCredentials
from apps.shared.errors import BaseError
from apps.users.crud import UsersCRUD
from apps.users.domain import User, UserLoginRequest
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.expire_minutes.access_token
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.secret_keys.authentication,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.expire_minutes.refresh_token
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.secret_keys.refresh,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str):
        if not pwd_context.verify(plain_password, hashed_password):
            raise BadCredentials("Invalid password")

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @classmethod
    async def authenticate_user(cls, user_login_schema: UserLoginRequest):
        user: User = await UsersCRUD().get_by_email(
            email=user_login_schema.email
        )
        cls.verify_password(user_login_schema.password, user.hashed_password)

        return user

    @staticmethod
    async def add_access_token_to_blacklist(token: InternalToken):
        """Currently we do not check if the token is in that blacklist
        as far as the redis client implementation is not working.
        """
        # key = "tokens-blacklist"
        # cache = RedisCache()
        # await cache.set(
        #     key=f"{key}:{token.raw_token}",
        #     val="",
        #     expire_after=token.payload.exp,
        # )
        raise BaseError("Currently this feature is not implemented.")
