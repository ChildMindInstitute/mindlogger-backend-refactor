import uuid

from fastapi import Body, Depends

from apps.activity_assignments.domain.assignments import ActivitiesAssignments, ActivitiesAssignmentsCreate
from apps.activity_assignments.service import ActivityAssignmentService
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
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
    
    
async def unassignments_create(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ActivitiesAssignmentsCreate = Body(...),
    session=Depends(get_session),
) -> Response[ActivitiesAssignments]:
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
    
    schema : ActivitiesAssignmentsCreate
        The schema containing the list of assignments to be unassigned.
    
    session : Depends, optional
        The database session (automatically injected).

    Returns:
    --------
    Response[ActivitiesAssignments]
        A response object containing the updated list of assignments for the applet.
    """
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_activity_assignment_access(applet_id)
        assignments = await ActivityAssignmentService(session).unassign_many(applet_id, schema.assignments)

    return Response(
        result=ActivitiesAssignments(
            applet_id=applet_id,
            assignments=assignments,
        )
    )
    