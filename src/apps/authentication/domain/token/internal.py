import uuid
from enum import StrEnum

from pydantic import EmailStr

from apps.shared.domain.base import InternalModel
from infrastructure.http.domain import MindloggerContentSource


class TokenPurpose(StrEnum):
    """This enumeration is used for internal needs (cache, ...)."""

    ACCESS = "access"
    REFRESH = "refresh"
    MFA = "mfa"
    DOWNLOAD_RECOVERY_CODES = "download_recovery_codes"


class JWTClaim(StrEnum):
    sub = "sub"
    jti = "jti"
    exp = "exp"
    rjti = "rjti"
    mfa_session_id = "mfa_session_id"
    client = "client"
    family = "family"


class TokenPayload(InternalModel):
    sub: uuid.UUID
    exp: int
    jti: str
    rjti: str | None = None
    # Which client the token was issued to (Mindlogger-Content-Source header).
    # None for tokens issued before the claim existed or to clients that do not
    # send the header
    client: MindloggerContentSource | None = None
    # Token family (the login refresh token's jti). Shared by every access/refresh
    # token descended from one login, so a whole rotated chain can be revoked at once.
    # None for tokens issued before the claim existed.
    family: str | None = None


class InternalToken(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    payload: TokenPayload
    raw_token: str | None = None


class MFATokenPayload(InternalModel):
    """Payload for MFA tokens."""

    mfa_session_id: str  # Redis session ID
    exp: int  # Expiration time stamp
    jti: str  # Token ID to prevent replay
    purpose: str = "mfa"  # Default purpose set to "mfa" for type checking


class TokenInfo(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    email: EmailStr
    user_id: int
    token_purpose: str
    raw_token: str
