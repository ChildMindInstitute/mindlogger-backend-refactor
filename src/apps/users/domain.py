from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicUser",
    "UserCreate",
    "UserLoginRequest",
    "UserCreate",
    "User",
    "UserCreateRequest",
]


class _UserBase(BaseModel):
    email: EmailStr

    def __str__(self) -> str:
        return self.email


class UserCreateRequest(_UserBase, PublicModel):
    full_name: str
    password: str


class UserLoginRequest(_UserBase, PublicModel):
    password: str


class UserCreate(_UserBase, InternalModel):
    full_name: str
    hashed_password: str


class UserUpdate(InternalModel):
    """This model represents user `update request` data model."""

    full_name: str


class UserDelete(InternalModel):
    """This model is used in order to represent internal user delete DTO."""

    is_deleted: bool = True


class User(UserCreate):
    id: PositiveInt


class PublicUser(_UserBase, PublicModel):
    """Public user data model."""

    full_name: str
    id: PositiveInt
