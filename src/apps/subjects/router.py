from fastapi import Body, Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.deps import get_current_user
from apps.shared.domain import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE, Response, ResponseMulti
from apps.subjects.api import (
    create_relation,
    create_subject,
    create_temporary_multiinformant_relation,
    delete_relation,
    delete_subject,
    get_subject,
    get_target_subjects_by_respondent,
    update_subject,
)
from apps.subjects.domain import (
    Subject,
    SubjectCreateRequest,
    SubjectCreateResponse,
    SubjectFull,
    SubjectReadResponse,
    SubjectReadResponseWithDataAccess,
    TargetSubjectByRespondentResponse,
)
from apps.users import User
from infrastructure.database.deps import get_session

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post(
    "",
    response_model=Response[SubjectCreateResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectCreateResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)
async def create_shell_account(
    user: User = Depends(get_current_user),
    schema: SubjectCreateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> Response[Subject]:
    return await create_subject(user, schema, session)


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
    response_model=Response[SubjectReadResponseWithDataAccess],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[SubjectReadResponseWithDataAccess]},
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

router.post(
    "/{subject_id}/relations/{source_subject_id}/multiinformant-assessment",
    response_model=Response[SubjectFull],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_201_CREATED: {"model": Response[SubjectFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_temporary_multiinformant_relation)


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

router.get(
    "/respondent/{respondent_subject_id}/activity-or-flow/{activity_or_flow_id}",
    response_model=ResponseMulti[TargetSubjectByRespondentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[TargetSubjectByRespondentResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_target_subjects_by_respondent)
