from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.api import create_integration, disable_integration, enable_integration
from apps.integrations.loris.domain.loris_projects import LorisProjects
from apps.shared.domain import Response
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/integrations", tags=["Integration"])


router.post(
    "/",
    description="This endpoint is used to enable integration\
           options for a workspace",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(enable_integration)

router.delete(
    "/",
    description="This endpoint is used to remove integrations\
           from a workspace",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(disable_integration)

router.post(
    "/{type}",
    description="This endpoint is used to create integrations",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[LorisProjects]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_integration)
