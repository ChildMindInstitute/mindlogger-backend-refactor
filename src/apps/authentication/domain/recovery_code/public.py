from datetime import datetime
from uuid import UUID

from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.users.domain import PublicUser

__all__ = [
    "PublicRecoveryCode",
    "RecoveryCodeView",
    "RecoveryCodesListResponse",
    "RecoveryCodeVerifyRequest",
    "RecoveryCodeVerifyResponse",
]


class PublicRecoveryCode(PublicModel):
    id: UUID
    used: bool
    used_at: datetime | None
    created_at: datetime


class RecoveryCodeView(PublicModel):
    """Single recovery code with decrypted value and usage status.

    Used for API responses when viewing recovery codes.
    """

    code: str  # Decrypted recovery code (e.g., "ABC12-DEF34")
    used: bool  # Whether this code has been used
    used_at: datetime | None = None  # When it was used (if used)


class RecoveryCodesListResponse(PublicModel):
    """Response model for listing user's recovery codes.

    Contains all codes with usage statistics.
    """

    codes: list[RecoveryCodeView]  # List of recovery codes with status
    total: int  # Total number of codes
    unused_count: int  # Number of unused codes remaining


class RecoveryCodeVerifyRequest(PublicModel):
    """Request model for verifying recovery code during MFA login.

    Used when user chooses to authenticate with recovery code instead of TOTP.
    """

    mfa_token: str  # JWT token from MFA session
    code: str  # Recovery code (format: XXXXX-XXXXX)
    device_id: str | None = None  # Optional device identifier


class RecoveryCodeVerifyResponse(PublicModel):
    """Response after successful recovery code verification.

    Returns authentication tokens similar to successful TOTP verification.
    Matches the structure of UserLogin response from login flow.
    """

    token: Token  # Access and refresh tokens
    user: PublicUser  # User information
