from pydantic import EmailStr

from apps.shared.domain import PublicModel
from apps.shared.domain.base import InternalModel
from config import settings


class Token(PublicModel):
    """This class is a public data model we send to the user."""

    access_token: str
    token_type: str = settings.authentication.token_type


class TokenPayload(InternalModel):
    sub: EmailStr
    exp: int


class InternalToken(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of hte JWT token.
    """

    payload: TokenPayload
    raw_token: str
