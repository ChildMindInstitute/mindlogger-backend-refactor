from pydantic import EmailStr

from apps.shared.domain import PublicModel


class TokenCreate(PublicModel):
    email: EmailStr
    access_token: str
    refresh_token: str


class TokenDeleteRequest(PublicModel):
    access_token: str


class Token(TokenCreate):
    id: int
