import uuid

from pydantic import EmailStr

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


class InitiateTransfer(InternalModel):
    email: EmailStr
