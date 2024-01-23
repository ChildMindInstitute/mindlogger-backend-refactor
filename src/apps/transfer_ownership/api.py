import uuid

from fastapi import Body, Depends

from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.transfer_ownership.domain import InitiateTransfer
from apps.transfer_ownership.service import TransferService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def transfer_initiate(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    transfer: InitiateTransfer = Body(...),
    session=Depends(get_session),
) -> None:
    """Initiate a transfer of ownership of an applet."""
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(
            session, user.id
        ).check_create_transfer_ownership_access(applet_id)
        await TransferService(session, user).initiate_transfer(
            applet_id, transfer
        )


async def transfer_accept(
    applet_id: uuid.UUID,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Respond to a transfer of ownership of an applet."""
    async with atomic(session):
        await TransferService(session, user).accept_transfer(applet_id, key)


async def transfer_decline(
    applet_id: uuid.UUID,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Decline a transfer of ownership of an applet."""
    async with atomic(session):
        await TransferService(session, user).decline_transfer(applet_id, key)
