import uuid
from enum import StrEnum

from pydantic import EmailStr

from apps.shared.domain.base import InternalModel


class TokenPurpose(StrEnum):
    """This enumeration is used for internal needs (cache, ...)."""

    ACCESS = "access"
    REFRESH = "refresh"
    MFA = "mfa"


class JWTClaim(StrEnum):
    sub = "sub"
    jti = "jti"
    exp = "exp"
    rjti = "rjti"
    mfa_session_id = "mfa_session_id"


class TokenPayload(InternalModel):
    sub: uuid.UUID
    exp: int
    jti: str
    rjti: str | None = None


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
