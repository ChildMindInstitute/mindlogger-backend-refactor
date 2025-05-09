import uuid

from fastapi import Body, Depends

from apps.activities.crud import ActivitiesCRUD
from apps.authentication.deps import get_current_user
from apps.integrations.oneup_health.domain import OneupHealthToken
from apps.integrations.oneup_health.service.oneup_health import OneupHealthService
from apps.integrations.oneup_health.service.task import task_ingest_user_data
from apps.shared.domain import InternalModel, Response
from apps.shared.exception import NotFoundError
from apps.subjects.services import SubjectsService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def retrieve_token(
    subject_id: uuid.UUID, user: User = Depends(get_current_user), session=Depends(get_session)
) -> Response[OneupHealthToken]:
    async with atomic(session):
        subjects_service = SubjectsService(session, user.id)
        subject = await subjects_service.exist_by_id(subject_id)

        applet_id = subject.applet_id
        await CheckAccessService(session, user.id).check_answer_create_access(applet_id)

        oneup_health_service = OneupHealthService()

        code = None
        oneup_user_id = subject.meta.get("oneup_user_id") if subject.meta else None
        if oneup_user_id is None:
            response = await oneup_health_service.create_user(subject.id)
            code = response.get("code")
            oneup_user_id = int(response["oneup_user_id"])
            await subjects_service.update(subject.id, meta={"oneup_user_id": oneup_user_id})

        token = await oneup_health_service.retrieve_token(submit_id=subject.id, code=code)

        return Response(result=OneupHealthToken(oneup_user_id=oneup_user_id, **token))


async def retrieve_token_by_submit_id_and_activity_id(
    applet_id: uuid.UUID,
    submit_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[OneupHealthToken]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_answer_create_access(applet_id)

        activity = await ActivitiesCRUD(session).get_by_id(activity_id)
        if activity is None or activity.applet_id != applet_id:
            raise NotFoundError("Activity does not belong to the applet")

        oneup_health_service = OneupHealthService()

        response = await oneup_health_service.create_user(submit_id, activity_id)
        oneup_user_id = int(response["oneup_user_id"])
        code = response.get("code")

        token = await oneup_health_service.retrieve_token(submit_id=submit_id, activity_id=activity_id, code=code)

        return Response(result=OneupHealthToken(oneup_user_id=oneup_user_id, **token))


class EHRTriggerInput(InternalModel):
    activity_id: uuid.UUID
    applet_id: uuid.UUID
    submit_id: uuid.UUID


async def trigger_data_fetch(trigger_input: EHRTriggerInput = Body(...)):
    await task_ingest_user_data.kicker().kiq(
        applet_id=trigger_input.applet_id,
        submit_id=trigger_input.submit_id,
        activity_id=trigger_input.activity_id,
    )

    return Response(result="ok")
