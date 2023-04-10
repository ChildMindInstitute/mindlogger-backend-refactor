from fastapi.routing import APIRouter
from starlette import status

from apps.answers.api import create_answer
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/answers", tags=["Answers"])

# Answers for activity item create
router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(create_answer)
