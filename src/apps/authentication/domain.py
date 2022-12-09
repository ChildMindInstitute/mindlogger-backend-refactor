from pydantic import EmailStr

from apps.shared.domain import PublicModel
from apps.shared.domain.base import InternalModel
from config import settings


class Token(PublicModel):
    access_token: str
    token_type: str = settings.authentication.token_type


class TokenPayload(InternalModel):
    sub: EmailStr
    exp: int


class TokenRichPayload(InternalModel):
    payload: TokenPayload
    raw_token: str
