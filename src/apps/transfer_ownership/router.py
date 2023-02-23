from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.transfer_ownership.api import (
    transfer_accept,
    transfer_decline,
    transfer_initiate,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

# Initiate a transfer of ownership of an applet.
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

# Accept a transfer of ownership of an applet.
router.post(
    "/{applet_id}/transferOwnership/{key}",
    response_model=None,
    responses={
        status.HTTP_200_OK: {"model": None},
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(transfer_accept)

# Decline a transfer of ownership of an applet.
router.delete(
    "/{applet_id}/transferOwnership/{key}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(transfer_decline)
