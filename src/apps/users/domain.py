from uuid import UUID

from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicUser",
    "UserCreate",
    "UserCreate",
    "User",
    "UserCreateRequest",
    "UserUpdateRequest",
    "ChangePasswordRequest",
    "UserChangePassword",
    "PasswordRecoveryRequest",
    "PasswordRecoveryInfo",
    "PasswordRecoveryApproveRequest",
]


class _UserBase(BaseModel):
    email: EmailStr

    def __str__(self) -> str:
        return self.email


class UserCreateRequest(_UserBase, PublicModel):
    first_name: str
    last_name: str
    nickname: str
    password: str


class UserCreate(_UserBase, InternalModel):
    first_name: str
    last_name: str
    nickname: str
    hashed_password: str


class UserUpdateRequest(InternalModel):
    """This model represents user `update request` data model."""

    first_name: str
    last_name: str
    nickname: str


class User(UserCreate):
    id: PositiveInt


class PublicUser(_UserBase, PublicModel):
    """Public user data model."""

    first_name: str
    last_name: str
    nickname: str
    id: PositiveInt


class ChangePasswordRequest(InternalModel):
    """This model represents change password data model."""

    password: str
    prev_password: str


class UserChangePassword(InternalModel):
    """This model represents user `update request` data model."""

    hashed_password: str


class PasswordRecoveryRequest(InternalModel):
    """This model represents password recovery request
    for password recover.
    """

    email: EmailStr


class PasswordRecoveryInfo(InternalModel):
    """This is a password recovery representation
    for internal needs.
    """

    email: EmailStr
    user_id: int
    key: UUID


class PasswordRecoveryApproveRequest(InternalModel):
    """This model represents password recovery approve request
    for password recover.
    """

    email: EmailStr
    key: UUID
    password: str
