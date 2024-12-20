import uuid

from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.answers.deps.preprocess_arbitrary import get_answer_session
from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain.domain import PublicListOfVisits, UploadableAnswersResponse, VisitsForUsers
from apps.integrations.loris.domain.loris_projects import LorisProjects
from apps.integrations.loris.service.loris import LorisIntegrationService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database.deps import get_session

__all__ = ["start_transmit_process", "visits_list", "users_info_with_visits", "get_loris_projects"]


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
    # TODO move to worker
    # TODO block job in progress
    # TODO mark answers as integrated to loris
    background_tasks.add_task(integration, applet_id, session, user, users_and_visits)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)


async def visits_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> PublicListOfVisits:
    visits = await LorisIntegrationService(applet_id, session, user).get_visits_list()
    return PublicListOfVisits(visits=visits, count=len(visits))


async def users_info_with_visits(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> UploadableAnswersResponse:
    await CheckAccessService(session, user.id).check_answer_publishing_access(applet_id)
    loris_service = LorisIntegrationService(applet_id, session, user, answer_session=answer_session)
    # TODO move to worker
    info, count = await loris_service.get_uploadable_answers()
    return UploadableAnswersResponse(result=info, count=count)


async def get_loris_projects(
    hostname: str,
    username: str,
    password: str,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> LorisProjects:
    return await LorisIntegrationService(
        uuid.UUID("00000000-0000-0000-0000-000000000000"), session=session, user=user
    ).get_loris_projects(hostname, username, password)
