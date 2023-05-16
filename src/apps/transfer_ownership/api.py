import uuid

from fastapi import Body, Depends

from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.schedule.service import ScheduleService
from apps.shared.exception import NotFoundError
from apps.transfer_ownership.domain import InitiateTransfer
from apps.transfer_ownership.service import TransferService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager


async def transfer_initiate(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    transfer: InitiateTransfer = Body(...),
    session=Depends(session_manager.get_session),
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
    session=Depends(session_manager.get_session),
) -> None:
    """Respond to a transfer of ownership of an applet."""
    async with atomic(session):
        await TransferService(session, user).accept_transfer(applet_id, key)
        try:
            await ScheduleService(session).delete_all_schedules(applet_id)
        except NotFoundError:
            pass


async def transfer_decline(
    applet_id: uuid.UUID,
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> None:
    """Decline a transfer of ownership of an applet."""
    async with atomic(session):
        await TransferService(session, user).decline_transfer(applet_id, key)
