import uuid
from datetime import datetime, timedelta, timezone

import jwt

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken, JWTClaim, TokenPayload, TokenPurpose
from apps.authentication.errors import BadCredentials, InvalidCredentials
from apps.authentication.services.core import TokensService
from apps.shared.bcrypt import get_password_hash, verify
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from config import settings

__all__ = ["AuthenticationService"]


class AuthenticationService:
    def __init__(self, session) -> None:
        self.session = session

    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expires_delta = timedelta(minutes=settings.authentication.access_token.expiration)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.setdefault(JWTClaim.exp, expire)
        to_encode.setdefault(JWTClaim.jti, str(uuid.uuid4()))
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.access_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expires_delta = timedelta(minutes=settings.authentication.refresh_token.expiration)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.setdefault(JWTClaim.exp, expire)
        to_encode.setdefault(JWTClaim.jti, str(uuid.uuid4()))
        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.refresh_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str, raise_exception=True) -> bool:
        valid = verify(plain_password, hashed_password)
        if not valid and raise_exception:
            raise BadCredentials()
        return valid

    @staticmethod
    def get_password_hash(password: str) -> str:
        return get_password_hash(password)

    async def authenticate_user(self, user_login_schema: UserLoginRequest) -> User:
        user: User = await UsersCRUD(self.session).get_by_email(email=user_login_schema.email)
        if not self.verify_password(user_login_schema.password, user.hashed_password, False):
            raise InvalidCredentials()
        return user

    def _get_refresh_token_by_access(self, token: InternalToken) -> InternalToken | None:
        if not token.payload.rjti:
            return None

        access_exp = datetime.fromtimestamp(token.payload.exp, timezone.utc)
        refresh_expires_delta = timedelta(minutes=settings.authentication.refresh_token.expiration)
        access_expires_delta = timedelta(minutes=settings.authentication.access_token.expiration)
        expire = access_exp - access_expires_delta + refresh_expires_delta
        refresh_token = InternalToken(
            payload=TokenPayload(
                sub=token.payload.sub,
                exp=int(expire.timestamp()),
                jti=token.payload.rjti,
            )
        )
        return refresh_token

    @staticmethod
    def extract_token_payload(token: str, key: str) -> TokenPayload:
        payload = jwt.decode(token, key, algorithms=[settings.authentication.algorithm])
        return TokenPayload(**payload)

    async def revoke_token(self, token: InternalToken, type_: TokenPurpose) -> None:
        """Add token to blacklist."""
        await TokensService(self.session).revoke(token, type_)
        if type_ == TokenPurpose.ACCESS:
            if refresh_token := self._get_refresh_token_by_access(token):
                await TokensService(self.session).revoke(refresh_token, TokenPurpose.REFRESH)

    async def is_revoked(self, token: InternalToken):
        return await TokensService(self.session).is_revoked(token)

    async def update_last_seen_at(self, user: User):
        """Update last seen at, but only every 15 minutes."""

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if user.last_seen_at is None or now - user.last_seen_at > timedelta(minutes=15):
            await UsersCRUD(self.session).update_last_seen_by_id(user.id)
