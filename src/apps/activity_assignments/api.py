import uuid

from fastapi import Body, Depends

from apps.activity_assignments.domain.assignments import (
    ActivitiesAssignments,
    ActivitiesAssignmentsCreate,
    ActivitiesAssignmentsDelete,
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
    """
    Creates multiple activity assignments for a specified applet.

    This endpoint allows authorized users to assign activities or flows to participants
    by creating new assignment records in the database.

    Parameters:
    -----------
    applet_id : uuid.UUID
        The ID of the applet for which assignments are being created.

    user : User, optional
        The current user making the request (automatically injected).

    schema : ActivitiesAssignmentsCreate
        The schema containing the list of assignments to be created.

    session : Depends, optional
        The database session (automatically injected).

    Returns:
    --------
    Response[ActivitiesAssignments]
        A response object containing the newly created assignments for the applet.
    """
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


async def assignment_delete(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ActivitiesAssignmentsDelete = Body(...),
    session=Depends(get_session),
) -> None:
    """
    Unassigns multiple activity assignments for a specified applet.

    This endpoint allows authorized users to unassign activities or flows from
    participants by marking the corresponding assignments as deleted.

    Parameters:
    -----------
    applet_id : uuid.UUID
        The ID of the applet from which assignments are being unassigned.

    user : User, optional
        The current user making the request (automatically injected).

    schema : ActivitiesAssignmentsDelete
        The schema containing the list of assignments to be unassigned.

    session : Depends, optional
        The database session (automatically injected).
    """
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_activity_assignment_access(applet_id)
        await ActivityAssignmentService(session).unassign_many(schema.assignments)


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
        raise NotFoundError(f"User doesn't have subject role in applet {applet_id}")

    assignments = await ActivityAssignmentService(session).get_all_by_subject(
        applet_id, respondent_subject.id, match_by="respondent"
    )

    return Response(
        result=ActivitiesAssignmentsWithSubjects(
            applet_id=applet_id,
            assignments=assignments,
        )
    )
