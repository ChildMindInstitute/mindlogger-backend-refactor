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
