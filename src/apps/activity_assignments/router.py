from fastapi.routing import APIRouter
from starlette import status

from apps.activity_assignments.api import assignments_create
from apps.activity_assignments.domain.assignments import ActivitiesAssignments
from apps.shared.domain import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE, Response

router = APIRouter(prefix="/assignments", tags=["Activity assignments"])

router.post(
    "/applet/{applet_id}",
    description="""Create a set of activity assignments. For each
                assignment, provide respondent ID (or if pending
                invite, then invitation ID), activity or activity
                flow ID, and optionally, target subject ID.
                """,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[ActivitiesAssignments]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(assignments_create)
