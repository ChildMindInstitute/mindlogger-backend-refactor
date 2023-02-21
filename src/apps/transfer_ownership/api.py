import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.transfer_ownership.domain import InitiateTransfer, TransferResponse
from apps.transfer_ownership.service import TransferService
from apps.users.domain import User

__all__ = [
    "transfer_initiate",
    "transfer_respond",
]


async def transfer_initiate(
    applet_id: int,
    user: User = Depends(get_current_user),
    transfer: InitiateTransfer = Body(...),
) -> None:
    """Initiate a transfer of ownership of an applet."""
    await TransferService(user).initiate_transfer(applet_id, transfer)


async def transfer_respond(
    applet_id: int,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    response: TransferResponse = Body(...),
) -> None:
    """Respond to a transfer of ownership of an applet."""
    await TransferService(user).respond_transfer(applet_id, key, response)
