from pydantic import EmailStr

from apps.shared.domain import PublicModel


class TokenCreate(PublicModel):
    email: EmailStr
    access_token: str
    refresh_token: str


class TokenRefresh(PublicModel):
    email: EmailStr
    access_token: str
    refresh_token: str


class TokenDeleteRequest(PublicModel):
    access_token: str


class RefreshAccessTokenRequest(PublicModel):
    refresh_token: str


class TokenPayload(PublicModel):
    sub: EmailStr
    exp: int


class Token(TokenCreate):
    id: int
