from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE
from apps.test_data.api import generate_test_data

router = APIRouter(prefix="/data")

# User create
router.post(
    "/generate_applet",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(generate_test_data)
