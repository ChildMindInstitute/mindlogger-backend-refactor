from datetime import datetime
from uuid import UUID

from apps.shared.domain import PublicModel

__all__ = ["PublicRecoveryCode"]


class PublicRecoveryCode(PublicModel):
    id: UUID
    used: bool
    used_at: datetime | None
    created_at: datetime
