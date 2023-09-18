import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import (
    InternalToken,
    JWTClaim,
    TokenPayload,
    TokenPurpose,
)
from apps.authentication.errors import BadCredentials, InvalidCredentials
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
        to_encode.setdefault(JWTClaim.exp, expire)
        to_encode.setdefault(JWTClaim.jti, str(uuid.uuid4()))
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
        to_encode.setdefault(JWTClaim.exp, expire)
        to_encode.setdefault(JWTClaim.jti, str(uuid.uuid4()))
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.refresh_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_password(
        plain_password: str, hashed_password: str, raise_exception=True
    ) -> bool:
        valid = pwd_context.verify(plain_password, hashed_password)
        if not valid and raise_exception:
            raise BadCredentials()
        return valid

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
        if not self.verify_password(
            user_login_schema.password, user.hashed_password, False
        ):
            raise InvalidCredentials()
        return user

    def _get_refresh_token_by_access(
        self, token: InternalToken
    ) -> InternalToken | None:
        if not token.payload.rjti:
            return None

        access_exp = datetime.utcfromtimestamp(token.payload.exp)
        refresh_expires_delta = timedelta(
            minutes=settings.authentication.refresh_token.expiration
        )
        access_expires_delta = timedelta(
            minutes=settings.authentication.access_token.expiration
        )
        expire = access_exp - access_expires_delta + refresh_expires_delta
        refresh_token = InternalToken(
            payload=TokenPayload(
                sub=token.payload.sub,
                exp=expire.replace(tzinfo=timezone.utc).timestamp(),
                jti=token.payload.rjti,
            )
        )
        return refresh_token

    async def revoke_token(self, token: InternalToken, type_: TokenPurpose):
        """Add token to blacklist in Redis."""
        await TokensService(self.session).revoke(token, type_)
        if type_ == TokenPurpose.ACCESS:
            if refresh_token := self._get_refresh_token_by_access(token):
                await TokensService(self.session).revoke(
                    refresh_token, TokenPurpose.REFRESH
                )

    async def is_revoked(self, token: InternalToken):
        return await TokensService(self.session).is_revoked(token)
