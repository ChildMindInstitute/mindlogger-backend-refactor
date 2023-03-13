from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import Response
from apps.shared.domain.response import (
    DEFAULT_OPENAPI_RESPONSE,
)
from apps.users.api import (
    user_create,
)
from apps.users.domain import PublicUser

router = APIRouter(prefix="/users", tags=["Users"])

# User create
router.post(
    "",
    response_model=Response[PublicUser],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_create)

