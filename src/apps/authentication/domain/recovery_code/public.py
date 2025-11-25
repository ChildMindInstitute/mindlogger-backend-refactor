from datetime import datetime
from uuid import UUID

from apps.shared.domain import PublicModel

__all__ = [
    "PublicRecoveryCode",
    "RecoveryCodeView",
    "RecoveryCodesListResponse",
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
