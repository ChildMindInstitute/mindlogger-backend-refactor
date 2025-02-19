from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.api import create_integration, delete_integration, retrieve_integration
from apps.integrations.domain import Integration
from apps.shared.domain import Response
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/integrations", tags=["Integration"])


router.post(
    "",
    description="This endpoint is used to create integrations",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[Integration]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_integration)

router.get(
    "",
    description="This endpoint is used to get integrations of an applet given a type",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[Integration]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(retrieve_integration)

router.delete(
    "/applet/{applet_id}",
    description="This endpoint is used to delete integrations",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(delete_integration)
