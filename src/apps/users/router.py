from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import Response
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.subjects.api import get_my_subject
from apps.subjects.domain import SubjectReadResponse
from apps.users.api import (
    password_recovery,
    password_recovery_approve,
    password_recovery_healthcheck,
    password_update,
    user_create,
    user_delete,
    user_retrieve,
    user_update,
)
from apps.users.domain import PublicUser

router = APIRouter(prefix="/users", tags=["Users"])

# User create
router.post(
    "",
    response_model=Response[PublicUser],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_create)

# User retrieve
router.get(
    "/me",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_retrieve)

# User update
router.put(
    "/me",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_update)

# User delete
router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_delete)

# Password update
router.put(
    "/me/password",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_update)

# Password recovery
router.post(
    "/me/password/recover",
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_recovery)

# Password recovery approve
router.post(
    "/me/password/recover/approve",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_recovery_approve)

# Password recovery healthcheck
router.get(
    "/me/password/recover/healthcheck",
)(password_recovery_healthcheck)

router.get(
    "/me/subjects/{applet_id}",
    response_model=Response[SubjectReadResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[SubjectReadResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_my_subject)
