from pydantic import EmailStr

from apps.shared.domain import PublicModel
from apps.shared.domain.base import InternalModel
from config import settings


class Token(PublicModel):
    """This class is a public data model we send to the user."""

    access_token: str
    refresh_token: str
    token_type: str = settings.authentication.token_type


class TokenPayload(InternalModel):
    sub: int
    exp: int


class InternalToken(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    payload: TokenPayload
    raw_token: str


class RefreshAccessTokenRequest(PublicModel):
    refresh_token: str


class TokenInfo(InternalModel):
    """This is used for internal needs.
    raw_token -- the raw value of the JWT token.
    """

    email: EmailStr
    user_id: int
    token_purpose: str
    raw_token: str
