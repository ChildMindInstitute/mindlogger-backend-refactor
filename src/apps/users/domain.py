from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicUser",
    "UserCreate",
    "UserLoginRequest",
    "UserCreate",
    "User",
    "UserSignUpRequest",
    "UserIsDeleted",
]


class _UserBase(BaseModel):
    email: EmailStr

    def __str__(self) -> str:
        return self.email


class UserSignUpRequest(_UserBase, PublicModel):
    full_name: str
    password: str


class UserLoginRequest(_UserBase, PublicModel):
    password: str


class UserCreate(_UserBase, InternalModel):
    full_name: str
    hashed_password: str


class UserIsDeleted(_UserBase, InternalModel):
    is_deleted: bool
    id: PositiveInt


class User(UserCreate):
    id: PositiveInt


class PublicUser(_UserBase, PublicModel):
    """Public user data model."""

    full_name: str
    id: PositiveInt
