import uuid

from fastapi import Depends

from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.integrations.oneup_health.domain import OneupHealthToken
from apps.integrations.oneup_health.service.oneup_health import OneupHealthService
from apps.shared.domain import Response
from apps.subjects.services import SubjectsService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def retrieve_token(
    applet_id: uuid.UUID, user: User = Depends(get_current_user), session=Depends(get_session)
) -> Response[OneupHealthToken]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)

        await CheckAccessService(session, user.id).check_answer_create_access(applet_id)

        subjects_service = SubjectsService(session, user.id)
        subject = await subjects_service.get_by_user_and_applet(user.id, applet_id)
        assert subject

        oneup_health_service = OneupHealthService()

        code = None
        oneup_user_id = subject.meta.get("oneup_user_id") if subject.meta else None
        if oneup_user_id is None:
            response = await oneup_health_service.create_user(subject.id)
            oneup_user_id = response["oneup_user_id"]
            await subjects_service.update(subject.id, meta={"oneup_user_id": oneup_user_id})
            code = response.get("code")

        token = await oneup_health_service.retrieve_token(subject_id=subject.id, code=code)

        return Response(result=OneupHealthToken(oneup_user_id=oneup_user_id, subject_id=subject.id, **token))
