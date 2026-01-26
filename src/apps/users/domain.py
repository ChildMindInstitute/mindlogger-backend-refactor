import datetime
import uuid
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from apps.shared.bcrypt import get_password_hash
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.hashing import hash_sha224
from apps.users.db.schemas import UserDeviceSchema
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
    "TOTPInitiateResponse",
    "TOTPVerifyRequest",
    "TOTPVerifyResponse",
    "MFADisableInitiateResponse",
    "MFADisableVerifyRequest",
    "MFADisableVerifyResponse",
    "MFADisableConfirmRequest",
    "MFADisableConfirmResponse",
    "RecoveryCodesViewInitiateResponse",
    "RecoveryCodesViewVerifyRequest",
]


class UserCreateRequest(PublicModel):
    """User creation request model."""

    email: EmailStr

    first_name: Annotated[
        str,
        Field(
            description="This field represents the user first name",
            min_length=1,
        ),
    ]
    last_name: Annotated[
        str,
        Field(
            description="This field represents the user last name",
            min_length=1,
        ),
    ]
    password: Annotated[
        str,
        Field(
            description="This field represents the user password",
            min_length=1,
        ),
    ]

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if " " in value:
            raise PasswordHasSpacesError()
        return value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class UserCreate(UserCreateRequest):
    # NOTE: pydantic before version 2 does not fully support properties.
    # but we can use them in our case, because we use properties directly
    # and we don't use for this model method dict
    @property
    def hashed_password(self) -> str:
        return get_password_hash(self.password)

    @property
    def hashed_email(self) -> str:
        return hash_sha224(self.email)


class UserUpdateRequest(InternalModel):
    """User update request model."""

    first_name: str
    last_name: str


class SoftDeleteUserRequest(UserUpdateRequest):
    """User update request model."""

    email: str
    is_deleted: bool = True


class User(InternalModel):
    """Internal user model."""

    email: str
    first_name: str
    last_name: str
    id: uuid.UUID
    is_super_admin: bool
    mfa_enabled: bool = False
    mfa_secret: str | None = None
    pending_mfa_secret: str | None = None
    pending_mfa_created_at: datetime.datetime | None = None
    last_totp_time_step: int | None = None
    recovery_codes_generated_at: datetime.datetime | None = None
    mfa_disabled_at: datetime.datetime | None = None  # Audit field - not exposed in PublicUser
    hashed_password: str
    email_encrypted: str | None = None
    last_seen_at: datetime.datetime | None = None

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name


class PublicUser(PublicModel):
    """Public-facing user model."""

    email: EmailStr | None = None
    first_name: str
    last_name: str
    id: uuid.UUID
    mfa_enabled: bool = False

    @classmethod
    def from_user(cls, user: User) -> "PublicUser":
        return cls(
            email=user.email_encrypted,
            first_name=user.first_name,
            last_name=user.last_name,
            id=user.id,
            mfa_enabled=user.mfa_enabled,
        )

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name


class ProlificPublicUser(InternalModel):
    """Simple flag indicating existence."""

    exists: bool


class ChangePasswordRequest(InternalModel):
    """Change password request."""

    password: str
    prev_password: str

    @field_validator("password", "prev_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if " " in value:
            raise PasswordHasSpacesError()
        return value


class UserChangePassword(InternalModel):
    """Internal model for updated password."""

    hashed_password: str


class PasswordRecoveryRequest(InternalModel):
    """Password recovery request."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class PasswordRecoveryInfo(InternalModel):
    """Internal password recovery info."""

    email: str
    user_id: uuid.UUID
    key: uuid.UUID


class PasswordRecoveryApproveRequest(InternalModel):
    """Approve password recovery request."""

    email: EmailStr
    key: uuid.UUID
    password: str


class AppInfoOS(PublicModel):
    name: str
    version: str


class AppInfo(PublicModel):
    os: AppInfoOS | None = None
    app_version: str | None = None


class UserDeviceCreate(AppInfo):
    device_id: str


class UserDevice(UserDeviceCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_schema(cls, schema: UserDeviceSchema):
        user_device = cls(
            id=schema.id,
            user_id=schema.user_id,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            device_id=schema.device_id,
            app_version=schema.app_version,
        )
        if schema.os_name:
            user_device.os = AppInfoOS(name=schema.os_name, version=schema.os_version)

        return user_device


class TOTPInitiateResponse(PublicModel):
    """Response for TOTP setup initiation."""

    provisioning_uri: Annotated[str, Field(description="URI for generating QR code in authenticator app")]
    message: Annotated[str, Field(description="Setup instructions for the user")]


class TOTPVerifyRequest(PublicModel):
    """TOTP verification request."""

    code: Annotated[
        str,
        Field(description="6-digit TOTP code from authenticator app", min_length=6, max_length=6, pattern=r"^\d{6}$"),
    ]


class TOTPVerifyResponse(PublicModel):
    """TOTP verification response."""

    message: Annotated[str, Field(description="Success message")]
    mfa_enabled: Annotated[bool, Field(description="Whether MFA is now enabled for the user")]
    recovery_codes: Annotated[
        list[str] | None,
        Field(
            description="Recovery codes generated during first-time MFA setup (displayed once only)",
        ),
    ] = None
    download_token: Annotated[
        str | None,
        Field(
            description="Short-lived download token (5 min) for downloading recovery codes as a file",
        ),
    ] = None


class MFADisableInitiateResponse(PublicModel):
    """Response when initiating MFA disable flow."""

    mfa_required: bool = True
    mfa_token: Annotated[str, Field(description="JWT token for MFA disable verification")]
    message: Annotated[str, Field(description="Instructions for completing MFA disable")]


class MFADisableVerifyRequest(PublicModel):
    """Request to verify TOTP code or recovery code and disable MFA."""

    mfa_token: Annotated[str, Field(description="JWT token from MFA disable initiation")]
    code: Annotated[
        str,
        Field(
            description="6-digit TOTP code from authenticator app or 11-character recovery code (XXXXX-XXXXX)",
            min_length=6,
            max_length=11,
        ),
    ]

    @field_validator("code")
    @classmethod
    def validate_code_length(cls, v: str) -> str:
        """Validate code is either 6 digits (TOTP) or 11 characters (recovery code)."""
        if len(v) not in (6, 11):
            raise ValueError("Code must be either 6 characters (TOTP) or 11 characters (recovery code)")
        return v


class MFADisableVerifyResponse(PublicModel):
    """Response after successfully validating code (MFA not yet disabled).

    This is step 2 of the 3-step disable flow. The code has been validated,
    but MFA is not yet disabled. Use the confirmation_token to complete the disable.
    """

    code_validated: bool = True
    confirmation_token: Annotated[str, Field(description="JWT token to confirm MFA disable")]
    message: Annotated[str, Field(description="Instructions for completing MFA disable")]


class MFADisableConfirmRequest(PublicModel):
    """Request to confirm MFA disable after successful code validation.

    This is step 3 of the 3-step disable flow.
    """

    confirmation_token: Annotated[str, Field(description="JWT token from successful code validation")]


class MFADisableConfirmResponse(PublicModel):
    """Response after successfully disabling MFA.

    This is the final response of the 3-step disable flow.
    """

    mfa_disabled: bool = True
    message: Annotated[str, Field(description="Success message confirming MFA has been disabled")]


class RecoveryCodesViewInitiateResponse(PublicModel):
    """Response when initiating recovery codes viewing flow."""

    mfa_required: bool = True
    mfa_token: Annotated[str, Field(description="JWT token for recovery codes view verification")]
    message: Annotated[str, Field(description="Instructions for viewing recovery codes")]


class RecoveryCodesViewVerifyRequest(PublicModel):
    """Request to verify TOTP code or recovery code and view recovery codes."""

    mfa_token: Annotated[str, Field(description="JWT token from recovery codes view initiation")]
    code: Annotated[
        str,
        Field(
            description="6-digit TOTP code from authenticator app or 11-character recovery code (XXXXX-XXXXX)",
            min_length=6,
            max_length=11,
        ),
    ]

    @field_validator("code")
    @classmethod
    def validate_code_length(cls, value: str) -> str:
        if len(value) not in (6, 11):
            raise ValueError("Code must be either 6 characters (TOTP) or 11 characters (recovery code)")
        return value
