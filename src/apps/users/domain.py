from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import BaseError, InternalModel, PublicModel

__all__ = [
    "UserCreate",
    "UserLoginRequest",
    "UserCreate",
    "User",
    "UsersError",
]


class _UserBase(BaseModel):
    email: EmailStr

    def __str__(self) -> str:
        return self.email


class UserSignUpRequest(_UserBase, PublicModel):
    username: str
    password: str


class UserLoginRequest(_UserBase, PublicModel):
    password: str


class UserCreate(InternalModel):
    email: EmailStr
    username: str
    hashed_password: str


class User(UserCreate):
    id: PositiveInt


class PublicUser(_UserBase, PublicModel):
    """Public user data model."""

    id: PositiveInt


class UsersError(BaseError):
    pass
