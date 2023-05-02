from fastapi.routing import APIRouter
from starlette import status

from apps.answers.api import (
    applet_activities_list,
    applet_answer_retrieve,
    applet_submit_date_list,
    create_answer,
    note_add,
    note_delete,
    note_edit,
    note_list,
)
from apps.answers.domain import (
    ActivityAnswerPublic,
    AnswerNoteDetailPublic,
    PublicAnswerDates,
    PublicAnsweredAppletActivity,
)
from apps.shared.domain import (
    AUTHENTICATION_ERROR_RESPONSES,
    Response,
    ResponseMulti,
)
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/answers", tags=["Answers"])

# Answers for activity item create
router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_answer)

router.get(
    "/applet/{applet_id}/activities",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicAnsweredAppletActivity],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activities_list)

router.get(
    "/applet/{applet_id}/dates",
    status_code=status.HTTP_200_OK,
    response_model=Response[PublicAnswerDates],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_submit_date_list)

router.get(
    "/applet/{applet_id}/answers/{answer_id}",
    responses={
        status.HTTP_200_OK: {"model": Response[ActivityAnswerPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_answer_retrieve)

router.post(
    "/applet/{applet_id}/answers/{answer_id}/notes",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_add)

router.get(
    "/applet/{applet_id}/answers/{answer_id}/notes",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[AnswerNoteDetailPublic],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_list)

router.put(
    "/applet/{applet_id}/answers/{answer_id}/notes/{note_id}",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_edit)

router.delete(
    "/applet/{applet_id}/answers/{answer_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_delete)
