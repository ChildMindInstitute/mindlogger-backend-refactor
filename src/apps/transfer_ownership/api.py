import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.transfer_ownership.domain import InitiateTransfer
from apps.transfer_ownership.service import TransferService
from apps.users.domain import User


async def transfer_initiate(
    applet_id: int,
    user: User = Depends(get_current_user),
    transfer: InitiateTransfer = Body(...),
) -> None:
    """Initiate a transfer of ownership of an applet."""
    await TransferService(user).initiate_transfer(applet_id, transfer)


async def transfer_accept(
    applet_id: int,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
) -> None:
    """Respond to a transfer of ownership of an applet."""
    await TransferService(user).accept_transfer(applet_id, key)


async def transfer_decline(
    applet_id: int,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
) -> None:
    """Decline a transfer of ownership of an applet."""
    await TransferService(user).decline_transfer(applet_id, key)
