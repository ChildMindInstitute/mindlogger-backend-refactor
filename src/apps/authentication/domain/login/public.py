from pydantic import EmailStr, root_validator

from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.shared.domain.custom_validations import lowercase_email
from apps.users.domain import PublicUser


class UserLogin(PublicModel):
    token: Token
    user: PublicUser


class UserLoginRequest(PublicModel):
    email: EmailStr
    password: str
    device_id: str | None = None

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)
