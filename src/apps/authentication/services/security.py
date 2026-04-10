import uuid
from datetime import datetime, timedelta, timezone

import jwt

from apps.authentication.domain.login import UserLoginRequest
from apps.authentication.domain.token import InternalToken, JWTClaim, TokenPayload, TokenPurpose
from apps.authentication.errors import (
    BadCredentials,
    InvalidCredentials,
    MFATokenExpiredError,
    MFATokenInvalidError,
    MFATokenMalformedError,
)
from apps.authentication.services.core import TokensService
from apps.shared.bcrypt import get_password_hash, verify
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from apps.users.password_validation import PasswordValidator
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
    def create_mfa_token(mfa_session_id: str) -> str:
        """
        Create JWT token for MFA verification.
        Args:
            mfa_session_id (str): The Redis session ID for MFA.
        Returns:
            str: Encoded JWT token for MFA.
        """
        expires_delta = timedelta(minutes=settings.authentication.mfa_token.expiration)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            JWTClaim.mfa_session_id: mfa_session_id,  # Redis session ID
            JWTClaim.exp: expire,  # Expiration time stamp
            JWTClaim.jti: str(uuid.uuid4()),  # Token ID to prevent replay
            "purpose": TokenPurpose.MFA,  # Token type
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.mfa_token.secret_key,
            algorithm=settings.authentication.algorithm,
        )

        return encoded_jwt

    @staticmethod
    def decode_mfa_token(token: str) -> str:
        """
        Decode and validate an MFA JWT token with comprehensive error handling.

        Args:
            token (str): The encoded JWT token for MFA.

        Returns:
            str: The MFA session ID from the token payload.

        Raises:
            MFATokenExpiredError: If token has expired
            MFATokenMalformedError: If token format is invalid
            MFATokenInvalidError: For other validation failures
        """
        try:
            payload = jwt.decode(
                token,
                settings.authentication.mfa_token.secret_key,
                algorithms=[settings.authentication.algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise MFATokenExpiredError()
        except jwt.InvalidSignatureError:
            raise MFATokenInvalidError()
        except jwt.DecodeError:
            raise MFATokenMalformedError()
        except Exception as e:
            # Catch-all for unexpected jwt errors
            raise MFATokenInvalidError() from e

        # Validate required claims exist
        mfa_session_id = payload.get(JWTClaim.mfa_session_id)
        if not mfa_session_id:
            raise MFATokenMalformedError()

        return mfa_session_id

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
        normalized = PasswordValidator.normalize(plain_password)
        if verify(normalized, hashed_password):
            return True
        # Fallback: try without normalization for pre-existing hashes
        if normalized != plain_password and verify(plain_password, hashed_password):
            return True
        if raise_exception:
            raise BadCredentials()
        return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        normalized = PasswordValidator.normalize(password)
        return get_password_hash(normalized)

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
    def create_download_recovery_codes_token(user_id: uuid.UUID) -> str:
        """
        Create a short-lived JWT token for downloading recovery codes.

        This token is issued after successful TOTP verification and allows
        the user to download their recovery codes within a limited time window.

        Args:
            user_id (uuid.UUID): The user's UUID

        Returns:
            str: Encoded JWT token for download authorization

        Token Payload:
            - sub: user_id (string)
            - purpose: "download_recovery_codes"
            - exp: current time + 5 minutes
            - jti: unique token ID
        """
        expires_delta = timedelta(seconds=settings.mfa.download_token_expiration_seconds)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            JWTClaim.sub: str(user_id),
            "purpose": TokenPurpose.DOWNLOAD_RECOVERY_CODES,
            JWTClaim.exp: expire,
            JWTClaim.jti: str(uuid.uuid4()),
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.authentication.mfa_token.secret_key,  # Reuse MFA token secret
            algorithm=settings.authentication.algorithm,
        )

        return encoded_jwt

    @staticmethod
    def validate_download_recovery_codes_token(token: str) -> uuid.UUID:
        """
        Validate and decode a download recovery codes JWT token.

        Args:
            token (str): The encoded JWT token

        Returns:
            uuid.UUID: The user_id from the token

        Raises:
            MFATokenExpiredError: If token has expired
            MFATokenMalformedError: If token format is invalid or missing required claims
            MFATokenInvalidError: For signature validation failures or wrong purpose
        """
        try:
            payload = jwt.decode(
                token,
                settings.authentication.mfa_token.secret_key,
                algorithms=[settings.authentication.algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise MFATokenExpiredError()
        except jwt.InvalidSignatureError:
            raise MFATokenInvalidError()
        except jwt.DecodeError:
            raise MFATokenMalformedError()
        except Exception as e:
            raise MFATokenInvalidError() from e

        # Validate required claims
        user_id_str = payload.get(JWTClaim.sub)
        purpose = payload.get("purpose")

        if not user_id_str or not purpose:
            raise MFATokenMalformedError()

        # Validate purpose matches
        if purpose != TokenPurpose.DOWNLOAD_RECOVERY_CODES:
            raise MFATokenInvalidError()

        # Convert user_id string to UUID
        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, AttributeError):
            raise MFATokenMalformedError()

        return user_id

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
