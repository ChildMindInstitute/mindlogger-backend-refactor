from pydantic import EmailStr, root_validator, validator

from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.shared.domain.custom_validations import lowercase_email
from apps.users.domain import PublicUser


class UserLogin(PublicModel):
    token: Token
    user: PublicUser


class UserLoginRequest(PublicModel):
    email: EmailStr
    password: str
    device_id: str | None = None

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)


class MFARequiredResponse(PublicModel):
    """Response when user has MFA enabled and must verify."""

    mfa_required: bool = True
    mfa_session_id: str  # Track session ID for MFA
    mfa_token: str  # JWT for MFA verification


class MFATOTPVerifyRequest(PublicModel):
    """Request model for verifying TOTP during MFA."""

    mfa_token: str  # JWT for MFA verification
    totp_code: str  # 6-digit TOTP code
    device_id: str | None = None  # Optional device identifier

    @validator("totp_code")
    def validate_totp_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise ValueError("TOTP code must be a 6-digit number")
        return value
