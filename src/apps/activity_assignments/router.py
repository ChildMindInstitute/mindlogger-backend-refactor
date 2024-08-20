from fastapi.routing import APIRouter
from starlette import status

from apps.activity_assignments.api import assignments_create, unassignments_create  # Import the new unassignment function
from apps.activity_assignments.domain.assignments import ActivitiesAssignments
from apps.shared.domain import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE, Response

router = APIRouter(prefix="/assignments", tags=["Activity assignments"])

router.post(
    "/applet/{applet_id}",
    description="""Create a set of activity assignments. For each
                assignment, provide respondent ID (or if pending
                invite, then invitation ID), activity or activity
                flow ID, and target subject ID.
                """,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[ActivitiesAssignments]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(assignments_create)

router.delete(
    "/applet/{applet_id}/unassigns",
    description="""Unassign a set of activity assignments. For each
                assignment, provide respondent ID (or if pending
                invite, then invitation ID), activity or activity
                flow ID, and target subject ID.
                """,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[ActivitiesAssignments]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(unassignments_create)