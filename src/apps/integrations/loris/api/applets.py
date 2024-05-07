import uuid

from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.authentication.deps import get_current_user
from apps.integrations.loris.service.loris import LorisIntegrationService
from apps.users.domain import User
from infrastructure.database.deps import get_session

__all__ = ["start_transmit_process"]


async def integration(applet_id: uuid.UUID, session, user):
    loris_service = LorisIntegrationService(applet_id, session, user)
    await loris_service.integration()


async def start_transmit_process(
    applet_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    background_tasks.add_task(integration, applet_id, session, user)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)
