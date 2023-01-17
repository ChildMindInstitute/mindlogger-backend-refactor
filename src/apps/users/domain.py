from uuid import UUID

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
    "UserUpdate",
    "UserLogoutRequest",
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
    device_id: str | None = None


class UserCreate(_UserBase, InternalModel):
    full_name: str
    hashed_password: str


class UserUpdate(InternalModel):
    """This model represents user `update request` data model."""

    full_name: str


class User(UserCreate):
    id: PositiveInt


class PublicUser(_UserBase, PublicModel):
    """Public user data model."""

    full_name: str
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


# NOTE: This message is not aligned yet. So, the mocked is used.
PASSWORD_RECOVERY_TEMPLATE = """
You have received this email to recovery your password.
Please follow the link: {link}
"""


class PasswordRecoveryApproveRequest(InternalModel):
    """This model represents password recovery approve request
    for password recover.
    """

    email: EmailStr
    key: UUID
    password: str


class UserLogoutRequest(InternalModel):
    device_id: str
