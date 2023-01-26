from fastapi.routing import APIRouter
from starlette import status

from apps.answers.api.answers import answer_create
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/answers", tags=["Answers"])

# Answers create
router.post(
    "",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(answer_create)
