from pydantic import EmailStr

from apps.shared.domain.base import InternalModel


class TokenPayload(InternalModel):
    sub: int
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
