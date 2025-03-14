import uuid

from fastapi import Depends

from apps.integrations.prolific.domain import ProlificCompletionCodeList, ProlificStudyValidation, ProlificUserInfo
from apps.integrations.prolific.service.prolific import ProlificIntegrationService
from apps.users.domain import ProlificPublicUser
from apps.users.services.prolific_user import ProlificUserService
from infrastructure.database.deps import get_session
from infrastructure.http.deps import get_language


async def get_public_prolific_integration(
    applet_id: uuid.UUID,
    study_id: str,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> ProlificStudyValidation:
    return await ProlificIntegrationService(session=session, applet_id=applet_id).validate_prolific_study(
        study_id, language
    )


async def get_study_completion_codes(
    study_id: str, applet_id: uuid.UUID, session=Depends(get_session)
) -> ProlificCompletionCodeList:
    return await ProlificIntegrationService(session=session, applet_id=applet_id).get_completion_codes(study_id)


async def prolific_user_exists(study_id: str, prolific_pid: str, session=Depends(get_session)) -> ProlificPublicUser:
    return await ProlificUserService(
        session=session, prolific_participant=ProlificUserInfo(study_id=study_id, prolific_pid=prolific_pid)
    ).user_exists()
