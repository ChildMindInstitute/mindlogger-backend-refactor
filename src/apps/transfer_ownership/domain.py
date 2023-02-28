import uuid

from pydantic import EmailStr
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "Transfer",
    "InitiateTransfer",
]


class Transfer(InternalModel):
    """Transfer ownership of an applet to another user."""

    email: EmailStr
    applet_id: PositiveInt
    key: uuid.UUID


class InitiateTransfer(PublicModel):
    email: EmailStr
