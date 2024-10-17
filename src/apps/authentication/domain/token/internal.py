import uuid
from enum import StrEnum

from pydantic import EmailStr

from apps.shared.domain.base import InternalModel


class TokenPurpose(StrEnum):
    """This enumeration is used for internal needs (cache, ...)."""

    ACCESS = "access"
    REFRESH = "refresh"


class JWTClaim(StrEnum):
    sub = "sub"
    jti = "jti"
    exp = "exp"
    rjti = "rjti"


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


class TokenInfo(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    email: EmailStr
    user_id: int
    token_purpose: str
    raw_token: str
