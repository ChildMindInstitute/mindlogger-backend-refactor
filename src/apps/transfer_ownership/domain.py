import uuid

from pydantic import EmailStr,validator 

from apps.shared.domain import InternalModel
from apps.transfer_ownership.constants import TransferOwnershipStatus

__all__ = [
    "Transfer",
    "InitiateTransfer",
]


class Transfer(InternalModel):
    """Transfer ownership of an applet to another user."""

    email: EmailStr
    applet_id: uuid.UUID
    key: uuid.UUID
    status: TransferOwnershipStatus
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID | None = None

    @validator("email",pre=True)
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase and strip whitespace."""
        return v.lower().strip()


class InitiateTransfer(InternalModel):
    email: EmailStr

    @validator("email",pre=True)
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase and strip whitespace."""
        return v.lower().strip()
