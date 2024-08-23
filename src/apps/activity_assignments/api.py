import uuid

from fastapi import Body, Depends

from apps.activity_assignments.domain.assignments import (
    ActivitiesAssignments,
    ActivitiesAssignmentsCreate,
    ActivitiesAssignmentsWithSubjects,
    ActivityAssignmentsListQueryParams,
)
from apps.activity_assignments.service import ActivityAssignmentService
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.shared.exception import NotFoundError
from apps.shared.query_params import QueryParams, parse_query_params
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def assignments_create(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ActivitiesAssignmentsCreate = Body(...),
    session=Depends(get_session),
) -> Response[ActivitiesAssignments]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_activity_assignment_access(applet_id)
        assignments = await ActivityAssignmentService(session).create_many(applet_id, schema.assignments)

    return Response(
        result=ActivitiesAssignments(
            applet_id=applet_id,
            assignments=assignments,
        )
    )


async def applet_assignments(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(ActivityAssignmentsListQueryParams)),
    session=Depends(get_session),
) -> Response[ActivitiesAssignments]:
    await CheckAccessService(session, user.id).check_applet_activity_assignment_access(applet_id)
    assignments = await ActivityAssignmentService(session).get_all(applet_id, query_params)

    return Response(
        result=ActivitiesAssignments(
            applet_id=applet_id,
            assignments=assignments,
        )
    )


async def applet_respondent_assignments(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[ActivitiesAssignmentsWithSubjects]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

    respondent_subject = await SubjectsService(session, user.id).get_by_user_and_applet(user.id, applet_id)
    if not respondent_subject:
        raise NotFoundError(f"User don't have subject role in applet {applet_id}")

    assignments = await ActivityAssignmentService(session).get_all_by_respondent(applet_id, respondent_subject.id)

    return Response(
        result=ActivitiesAssignmentsWithSubjects(
            applet_id=applet_id,
            assignments=assignments,
        )
    )
