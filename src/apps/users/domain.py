from pydantic import EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import BaseError, Model


class UserBase(Model):
    email: EmailStr

    def __str__(self) -> str:
        return self.email


class UserCreate(UserBase):
    username: str
    password: str


class UserInDB(UserBase):
    username: str
    hashed_password: str


class User(UserInDB):
    id: PositiveInt


class UserLogin(UserBase):
    password: str


class UsersError(BaseError):
    def __init__(self, message: str | None = None, *args, **kwargs) -> None:
        message = (
                message
                or "Can not find your user in the database. Please register first."
        )
        super().__init__(message, *args, **kwargs)
