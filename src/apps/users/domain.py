import uuid

from pydantic import BaseModel, EmailStr, Field, root_validator

from apps.shared.domain import InternalModel, PublicModel
from apps.shared.domain.custom_validations import lowercase_email

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
    # Has this type because in the descendant classes the hash gets here
    email: str

    def __str__(self) -> str:
        return self.email

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)


class UserCreateRequest(_UserBase, PublicModel):
    """This model represents user `create request` data model."""

    first_name: str = Field(
        description="This field represents the user first name",
        min_length=1,
    )
    last_name: str = Field(
        description="This field represents the user last name",
        min_length=1,
    )
    password: str = Field(
        description="This field represents the user password",
        min_length=1,
    )


class UserCreate(_UserBase, InternalModel):
    first_name: str
    last_name: str
    hashed_password: str


class UserUpdateRequest(InternalModel):
    """This model represents user `update request` data model."""

    first_name: str
    last_name: str


class User(UserCreate):
    id: uuid.UUID
    is_super_admin: bool
    email_encrypted: str | None


class PublicUser(PublicModel):
    """Public user data model."""

    email: EmailStr | None
    first_name: str
    last_name: str
    id: uuid.UUID

    @classmethod
    def from_user(cls, user: User) -> "PublicUser":
        return cls(
            email=user.email_encrypted,
            first_name=user.first_name,
            last_name=user.last_name,
            id=user.id,
        )


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

    email: str
    user_id: uuid.UUID
    key: uuid.UUID


class PasswordRecoveryApproveRequest(InternalModel):
    """This model represents password recovery approve request
    for password recover.
    """

    email: EmailStr
    key: uuid.UUID
    password: str
