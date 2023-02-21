from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.transfer_ownership.api import transfer_initiate, transfer_respond

router = APIRouter(prefix="/applets", tags=["Applets"])

# Invitations list
router.post(
    "/{applet_id}/transferOwnership",
    response_model=None,
    responses={
        status.HTTP_200_OK: {"model": None},
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(transfer_initiate)

router.post(
    "/{applet_id}/transferOwnership/{key}",
    response_model=None,
    responses={
        status.HTTP_200_OK: {"model": None},
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(transfer_respond)
