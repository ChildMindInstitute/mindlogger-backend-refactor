from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE
from apps.test_data.api import test_data_delete_generated, test_data_generate

router = APIRouter(prefix="/data")

# Create route for generating test data
router.post(
    "/generate_applet",
    status_code=status.HTTP_201_CREATED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(test_data_generate)


router.delete(
    "/generate_applet",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(test_data_delete_generated)
