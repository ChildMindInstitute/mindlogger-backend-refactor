from uuid import UUID

from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicUser",
    "UserCreate",
    "UserLoginRequest",
    "UserCreate",
    "UserDelete",
    "User",
    "UserCreateRequest",
    "UserUpdate",
    "ChangePasswordRequest",
    "UserChangePassword",
    "PasswordRecoveryRequest",
    "PasswordRecoveryInfo",
    "PASSWORD_RECOVERY_TEMPLATE",
    "PasswordRecoveryApproveRequest",
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


class ChangePasswordRequest(InternalModel):
    """This model represents change password data model."""

    password: str


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


PASSWORD_RECOVERY_TEMPLATE = """
You have received this email to recovery your password.
Please follow the link: {link}
"""


class PasswordRecoveryApproveRequest(InternalModel):
    """This model represents password recovery approve request
    for password recover.
    """

    token: UUID
    password: str
