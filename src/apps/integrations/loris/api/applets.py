import uuid

from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain import PublicListMultipleVisits, PublicListOfVisits, VisitsForUsers
from apps.integrations.loris.service.loris import LorisIntegrationService
from apps.users.domain import User
from infrastructure.database.deps import get_session

__all__ = [
    "start_transmit_process",
    "visits_list",
    "users_info_with_visits",
]


async def integration(applet_id: uuid.UUID, session, user, users_and_visits):
    loris_service = LorisIntegrationService(applet_id, session, user)
    await loris_service.integration(users_and_visits)


async def start_transmit_process(
    applet_id: uuid.UUID,
    users_and_visits: list[VisitsForUsers],
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    background_tasks.add_task(integration, applet_id, session, user, users_and_visits)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)


async def visits_list(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> PublicListOfVisits:
    visits = await LorisIntegrationService.get_visits_list()
    return PublicListOfVisits(visits=visits, count=len(visits))


async def users_info_with_visits(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> PublicListMultipleVisits:
    loris_service = LorisIntegrationService(applet_id, session, user)
    info = await loris_service.get_information_about_users_and_visits()
    return PublicListMultipleVisits(info=info, count=len(info))
