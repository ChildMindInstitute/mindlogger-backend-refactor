from fastapi.routing import APIRouter
from starlette import status

from apps.activity_assignments.api import (
    applet_assignments,
    applet_respondent_assignments,
    assignment_delete,
    assignments_create,
)
from apps.activity_assignments.domain.assignments import ActivitiesAssignments, ActivitiesAssignmentsWithSubjects
from apps.shared.domain import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE, Response

router = APIRouter(prefix="/assignments", tags=["Activity assignments"])

router.post(
    "/applet/{applet_id}",
    description="""Create a set of activity assignments. For each
                assignment, provide respondent subject ID (full account 
                or pending full account), target subject ID
                and activity or activity flow ID
                """,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[ActivitiesAssignments]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(assignments_create)

router.delete(
    "/applet/{applet_id}",
    description="""Unassign a set of activity assignments. For each
                assignment, provide respondent subject ID (full account
                or pending account), target subject ID, and activity or activity flow ID.
                """,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Successfully unassigned the activities or flows."},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(assignment_delete)

router.get(
    "/applet/{applet_id}",
    description="""Get all activity assignments for an applet.
                """,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivitiesAssignments]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_assignments)

# User endpoints
user_router = APIRouter(prefix="/users", tags=["Users"])

user_router.get(
    "/me/assignments/{applet_id}",
    description="""
    Get all activity assignments for logged-in respondent for an applet.
                """,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivitiesAssignmentsWithSubjects]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_respondent_assignments)
