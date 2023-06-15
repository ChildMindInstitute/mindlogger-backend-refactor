from fastapi.routing import APIRouter
from starlette import status

from apps.answers.api import (
    applet_activity_answer_retrieve,
    applet_activity_answers_list,
    applet_activity_assessment_create,
    applet_activity_assessment_retrieve,
    applet_activity_identifiers_retrieve,
    applet_activity_versions_retrieve,
    applet_answer_reviews_retrieve,
    applet_answers_export,
    applet_submit_date_list,
    create_anonymous_answer,
    create_answer,
    note_add,
    note_delete,
    note_edit,
    note_list,
    review_activity_list,
    summary_activity_list,
)
from apps.answers.domain import (
    ActivityAnswerPublic,
    AnswerNoteDetailPublic,
    AnswerReviewPublic,
    AppletActivityAnswerPublic,
    AssessmentAnswerPublic,
    PublicAnswerDates,
    PublicAnswerExport,
    PublicReviewActivity,
    PublicSummaryActivity,
    VersionPublic,
)
from apps.shared.domain import (
    AUTHENTICATION_ERROR_RESPONSES,
    Response,
    ResponseMulti,
)
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/answers", tags=["Answers"])
public_router = APIRouter(prefix="/public/answers", tags=["Answers"])

# Answers for activity item create
router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_answer)

# Anonymous Answers for activity item create
public_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_anonymous_answer)

router.get(
    "/applet/{applet_id}/review/activities",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicReviewActivity],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(review_activity_list)

router.get(
    "/applet/{applet_id}/summary/activities",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicSummaryActivity],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(summary_activity_list)

router.get(
    "/applet/{applet_id}/summary/activities/{activity_id}/identifiers",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[str]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_identifiers_retrieve)

router.get(
    "/applet/{applet_id}/summary/activities/{activity_id}/versions",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[VersionPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_versions_retrieve)

router.get(
    "/applet/{applet_id}/activities/{activity_id}/answers",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ResponseMulti[AppletActivityAnswerPublic]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_answers_list)

router.get(
    "/applet/{applet_id}/dates",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicAnswerDates]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_submit_date_list)

router.get(
    "/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivityAnswerPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_answer_retrieve)

router.get(
    "/applet/{applet_id}/answers/{answer_id}/reviews",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AnswerReviewPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_answer_reviews_retrieve)

router.get(
    "/applet/{applet_id}/answers/{answer_id}/assessment",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[AssessmentAnswerPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_assessment_retrieve)

router.post(
    "/applet/{applet_id}/answers/{answer_id}/assessment",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_activity_assessment_create)

router.post(
    "/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_add)

router.get(
    "/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[AnswerNoteDetailPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_list)

router.put(
    "/applet/{applet_id}/answers/{answer_id}/activities/"
    "{activity_id}/notes/{note_id}",
    # noqa: E501
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_edit)

router.delete(
    "/applet/{applet_id}/answers/{answer_id}/activities/"
    "{activity_id}/notes/{note_id}",
    # noqa: E501
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(note_delete)

router.get(
    "/applet/{applet_id}/data",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicAnswerExport]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_answers_export)
