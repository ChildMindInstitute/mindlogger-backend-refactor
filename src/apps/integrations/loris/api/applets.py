import uuid

from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain import PublicListOfVisits
from apps.integrations.loris.service.loris import LorisIntegrationService
from apps.shared.domain import ResponseMulti
from apps.users.domain import User
from infrastructure.database.deps import get_session

__all__ = [
    "start_transmit_process",
    "visits_list",
]


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


async def visits_list(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[PublicListOfVisits]:
    visits = await LorisIntegrationService.get_visits_list()
    return ResponseMulti(
        result=[PublicListOfVisits(visits=visits)],
        count=len(visits),
    )
