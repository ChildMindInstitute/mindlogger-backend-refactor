from fastapi.routing import APIRouter
from starlette import status

from apps.answers.api import (
    answer_activity_item_create,
    answer_flow_item_create,
)
from apps.answers.domain import PublicAnswerActivityItem, PublicAnswerFlowItem
from apps.shared.domain import Response
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/answers", tags=["Answers"])

# Answers activity item create
router.post(
    "/activity-items/{id_version}",
    description="""This endpoint using for adding new respondent answer 
    to database with linked to an activity-items
    """,
    response_model=Response[PublicAnswerActivityItem],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicAnswerActivityItem]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(answer_activity_item_create)

# Answers flow item create
router.post(
    "/flow-items/{id_version}",
    description="""This endpoint using for adding new respondent answer 
    to database with linked to an flow-items
    """,
    response_model=Response[PublicAnswerFlowItem],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicAnswerFlowItem]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(answer_flow_item_create)
