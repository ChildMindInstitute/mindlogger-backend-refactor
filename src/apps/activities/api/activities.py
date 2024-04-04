import asyncio
import uuid

from fastapi import Depends

from apps.activities.crud import ActivitiesCRUD
from apps.activities.domain.activity import ActivitySingleLanguageWithItemsDetailPublic
from apps.activities.filters import AppletActivityFilter
from apps.activities.services.activity import ActivityItemService, ActivityService
from apps.answers.deps.preprocess_arbitrary import get_answer_session
from apps.answers.service import AnswerService
from apps.applets.domain.applet import AppletActivitiesDetailsPublic, AppletSingleLanguageDetailMobilePublic
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.shared.query_params import QueryParams, parse_query_params
from apps.subjects.services import SubjectsService
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
        await CheckAccessService(session, user.id).check_applet_detail_access(schema.applet_id)
        activity = await ActivityService(session, user.id).get_single_language_by_id(activity_id, language)

    return Response(result=ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity))


async def public_activity_retrieve(
    id_: uuid.UUID,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitySingleLanguageWithItemsDetailPublic]:
    async with atomic(session):
        activity = await ActivityService(
            session, uuid.UUID("00000000-0000-0000-0000-000000000000")
        ).get_public_single_language_by_id(id_, language)

    return Response(result=ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity))


async def applet_activities(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AppletActivityFilter)),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AppletActivitiesDetailsPublic]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

        filters = AppletActivityFilter(**query_params.filters)

        applet_future = service.get_single_language_by_id(applet_id, language)
        subject_future = SubjectsService(session, user.id).get_by_user_and_applet(user.id, applet_id)
        activities_future = ActivityService(session, user.id).get_single_language_with_items_by_applet_id(
            applet_id, language
        )

        applet, subject, activities = await asyncio.gather(
            applet_future,
            subject_future,
            activities_future,
        )
        applet_detail = AppletSingleLanguageDetailMobilePublic.from_orm(applet)
        respondent_meta = {"nickname": subject.nickname if subject else None}

        for activity in activities:
            # Filter by `hasSubmitted` (if the activity has submitted answers)
            if filters.has_submitted is not None:
                latest_answer = await AnswerService(session, user.id, answer_session).get_latest_answer_by_activity_id(
                    applet_id, activity.id
                )
                if filters.has_submitted:
                    if latest_answer is None:
                        activities.remove(activity)
                else:
                    if latest_answer is not None:
                        activities.remove(activity)

            # Filter by `hasScore` (if the activity has score set to activity items)
            if filters.has_score is not None:
                activity_items = await ActivityItemService(session).get_single_language_by_activity_id(
                    activity.id, language
                )

                found_score = False
                for activity_item in activity_items:
                    if found_score:
                        break

                    options = getattr(activity_item.response_values, "options", [])
                    for option in options:
                        if option.score > 0:
                            found_score = True

                if filters.has_score:
                    if not found_score:
                        activities.remove(activity)
                else:
                    if found_score:
                        activities.remove(activity)

    result = AppletActivitiesDetailsPublic(
        activities_details=activities,
        applet_detail=applet_detail,
        respondent_meta=respondent_meta,
    )
    return Response(result=result)
