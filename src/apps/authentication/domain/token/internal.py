import uuid
from enum import Enum

from pydantic import EmailStr

from apps.shared.domain.base import InternalModel


class TokenPurpose(str, Enum):
    """This enumeration is used for internal needs (cache, ...)."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(InternalModel):
    sub: uuid.UUID
    exp: int


class InternalToken(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    payload: TokenPayload
    raw_token: str


class TokenInfo(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    email: EmailStr
    user_id: int
    token_purpose: str
    raw_token: str
