from pydantic import EmailStr

from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.users.domain import PublicUser


class UserLogin(PublicModel):
    token: Token
    user: PublicUser


class UserLoginRequest(PublicModel):
    email: EmailStr
    password: str
    device_id: str | None = None
