from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken
from apps.authentication.errors import BadCredentials
from apps.authentication.services.core import TokensService
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from config import settings

__all__ = ["AuthenticationService"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.access_token.expiration
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.access_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict):
        to_encode = data.copy()
        expires_delta = timedelta(
            minutes=settings.authentication.refresh_token.expiration
        )
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.refresh_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str):
        if not pwd_context.verify(plain_password, hashed_password):
            raise BadCredentials()

    @staticmethod
    def verify_password_and_hash(
        plain_password: str, hashed_password: str
    ) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    async def authenticate_user(self, user_login_schema: UserLoginRequest):
        user: User = await UsersCRUD(self.session).get_by_email(
            email=user_login_schema.email
        )
        self.verify_password(user_login_schema.password, user.hashed_password)

        return user

    async def add_access_token_to_blacklist(self, token: InternalToken):
        """Add access token to blacklist in Redis."""
        await TokensService(self.session).add_access_token_to_blacklist(token)

    async def fetch_all_tokens(self, email: str):
        """Finds all records for the specified Email."""
        return await TokensService(self.session).fetch_all(email)
