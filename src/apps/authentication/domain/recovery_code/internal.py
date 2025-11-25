import datetime
import uuid

from apps.shared.domain import InternalModel

__all__ = [
    "RecoveryCode",
    "RecoveryCodeCreate",
]


class RecoveryCodeCreate(InternalModel):
    """Model for creating a new recovery code."""

    user_id: uuid.UUID
    code_hash: str
    code_encrypted: str
    used: bool = False
    used_at: datetime.datetime | None = None


class RecoveryCode(RecoveryCodeCreate):
    """Full recovery code model with database fields."""

    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool
