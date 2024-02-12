from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    Response,
)
from apps.subjects.api import (
    create_relation,
    create_subject,
    delete_relation,
    delete_subject,
    get_subject,
    update_subject,
)
from apps.subjects.domain import Subject, SubjectFull, SubjectReadResponse

router = APIRouter(prefix="/subjects", tags=["Subjects"])

router.post(
    "",
    response_model=Response[Subject],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[Subject]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_subject)

router.put(
    "/{subject_id}",
    response_model=Response[SubjectReadResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[SubjectReadResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(update_subject)

router.delete(
    "/{subject_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(delete_subject)

router.get(
    "/{subject_id}",
    response_model=Response[SubjectReadResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[SubjectReadResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_subject)

router.post(
    "/{subject_id}/relations/{source_subject_id}",
    response_model=Response[SubjectFull],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_relation)


router.delete(
    "/{subject_id}/relations/{source_subject_id}",
    response_model=Response[SubjectFull],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(delete_relation)
