from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    Response,
)
from apps.subjects.api import add_respondent, create_subject
from apps.subjects.domain import Subject, SubjectFull

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


router.post(
    "/respondents",
    response_model=Response[SubjectFull],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(add_respondent)
