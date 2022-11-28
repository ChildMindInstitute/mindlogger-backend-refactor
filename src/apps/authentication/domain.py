from pydantic import EmailStr

from apps.shared.domain import Model


class Token(Model):
    access_token: str
    token_type: str


class TokenData(Model):
    email: str | None = None


class TokenInDB(Model):
    email: EmailStr
    access_token: str
    refresh_token: str


class TokenLogin(Model):
    access_token: str
    refresh_token: str
    token_type: str
