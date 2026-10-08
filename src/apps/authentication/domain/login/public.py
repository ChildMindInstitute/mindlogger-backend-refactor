from pydantic import EmailStr, field_validator

from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.users.domain import PublicUser


class UserLogin(PublicModel):
    token: Token
    user: PublicUser


class UserLoginRequest(PublicModel):
    email: EmailStr
    password: str
    device_id: str | None = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class MFARequiredResponse(PublicModel):
    """Response when user has MFA enabled and must verify."""

    mfa_required: bool = True
    mfa_session_id: str  # Track session ID for MFA
    mfa_token: str  # JWT for MFA verification
    user_id: str  # Only need ID for the client
    user_email: EmailStr  # Only need email for the client


class MSARequiredResponse(PublicModel):
    """Response when an admin user must accept the MSA before getting a session."""

    msa_required: bool = True
    msa_token: str  # JWT that only allows accepting the MSA
    version: str  # MSA version the user must accept
    user_id: str
    user_email: EmailStr


class MFATOTPVerifyRequest(PublicModel):
    """Request model for verifying TOTP during MFA."""

    mfa_token: str  # JWT for MFA verification
    totp_code: str  # 6-digit TOTP code
    device_id: str | None = None  # Optional device identifier

    @field_validator("totp_code")
    @classmethod
    def validate_totp_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise ValueError("TOTP code must be a 6-digit number")
        return value
