import uuid

from pydantic import BaseModel, EmailStr, Field

from apps.shared.domain import InternalModel, PublicModel
from apps.shared.encryption import decrypt, encrypt

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
    email: str

    def __str__(self) -> str:
        return self.email


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

    @property
    def encrypted_first_name(self) -> str | None:
        if self.first_name:
            return encrypt(bytes(self.first_name, "utf-8")).hex()
        return None

    @property
    def encrypted_last_name(self) -> str | None:
        if self.last_name:
            return encrypt(bytes(self.last_name, "utf-8")).hex()
        return None


class UserCreate(_UserBase, InternalModel):
    first_name: str
    last_name: str
    hashed_password: str


class UserUpdateRequest(InternalModel):
    """This model represents user `update request` data model."""

    first_name: str
    last_name: str

    @property
    def encrypted_first_name(self) -> str | None:
        if self.first_name:
            return encrypt(bytes(self.first_name, "utf-8")).hex()
        return None

    @property
    def encrypted_last_name(self) -> str | None:
        if self.last_name:
            return encrypt(bytes(self.last_name, "utf-8")).hex()
        return None


class User(UserCreate):
    id: uuid.UUID
    is_super_admin: bool
    email_encrypted: str | None

    @property
    def plain_email(self) -> str | None:
        if self.email_encrypted:
            return decrypt(bytes.fromhex(self.email_encrypted)).decode("utf-8")
        return None

    @property
    def plain_first_name(self) -> str | None:
        if self.first_name:
            try:
                return decrypt(bytes.fromhex(self.first_name)).decode("utf-8")
            except:
                return self.first_name
        return None

    @property
    def plain_last_name(self) -> str | None:
        if self.last_name:
            try:
                return decrypt(bytes.fromhex(self.last_name)).decode("utf-8")
            except:
                return self.last_name
        return None


class PublicUser(PublicModel):
    """Public user data model."""

    email: EmailStr | None
    first_name: str
    last_name: str
    id: uuid.UUID

    @classmethod
    def from_user(cls, user: User) -> "PublicUser":
        return cls(
            email=user.plain_email,
            first_name=user.plain_first_name,
            last_name=user.plain_last_name,
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
