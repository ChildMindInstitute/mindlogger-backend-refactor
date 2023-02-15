from fastapi import Depends

from apps.activities.domain.activity import ActivityExtendedDetailPublic
from apps.activities.services.activity import ActivityService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.users import User
from infrastructure.http import get_language


async def activity_retrieve(
    id_: int,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Response[ActivityExtendedDetailPublic]:
    activity = await ActivityService(user.id).get_single_language_by_id(
        id_, language
    )

    return Response(result=ActivityExtendedDetailPublic.from_orm(activity))
