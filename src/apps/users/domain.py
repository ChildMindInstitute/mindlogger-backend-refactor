import uuid

from pydantic import EmailStr, Field, root_validator, validator

from apps.shared.domain import InternalModel, PublicModel
from apps.shared.domain.custom_validations import lowercase_email
from apps.shared.hashing import hash_sha224
from apps.shared.passlib import get_password_hash
from apps.users.errors import PasswordHasSpacesError

__all__ = [
    "PublicUser",
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


class UserCreateRequest(PublicModel):
    """This model represents user `create request` data model."""

    email: EmailStr

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

    @validator("password")
    def validate_password(cls, value: str) -> str:
        if " " in value:
            raise PasswordHasSpacesError()
        return value

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)


class UserCreate(UserCreateRequest):
    # NOTE: pydantic before version 2 does not fully support properties.
    # but we can use them in our case, because we use properties directly
    # and we don't user for this model method dict
    @property
    def hashed_password(self) -> str:
        return get_password_hash(self.password)

    @property
    def hashed_email(self) -> str:
        return hash_sha224(self.email)


class UserUpdateRequest(InternalModel):
    """This model represents user `update request` data model."""

    first_name: str
    last_name: str


class User(InternalModel):
    email: str
    first_name: str
    last_name: str
    id: uuid.UUID
    is_super_admin: bool
    hashed_password: str
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

    @validator("password", "prev_password")
    def validate_password(cls, value: str) -> str:
        if " " in value:
            raise PasswordHasSpacesError()
        return value


class UserChangePassword(InternalModel):
    """This model represents user `update request` data model."""

    hashed_password: str


class PasswordRecoveryRequest(InternalModel):
    """This model represents password recovery request
    for password recover.
    """

    email: EmailStr

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)


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
