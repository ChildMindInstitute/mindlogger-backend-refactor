import uuid

from fastapi import Depends

from apps.activities.crud import ActivitiesCRUD
from apps.activities.domain.activity import (
    ActivitySingleLanguageWithItemsDetailPublic,
)
from apps.activities.services.activity import ActivityService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.users import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session
from infrastructure.http import get_language


async def activity_retrieve(
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitySingleLanguageWithItemsDetailPublic]:
    async with atomic(session):
        schema = await ActivitiesCRUD(session).get_by_id(activity_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(
            schema.applet_id
        )
        activity = await ActivityService(
            session, user.id
        ).get_single_language_by_id(activity_id, language)

    return Response(
        result=ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity)
    )


async def public_activity_retrieve(
    id_: uuid.UUID,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitySingleLanguageWithItemsDetailPublic]:
    async with atomic(session):
        activity = await ActivityService(
            session, uuid.UUID("00000000-0000-0000-0000-000000000000")
        ).get_public_single_language_by_id(id_, language)

    return Response(
        result=ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity)
    )
