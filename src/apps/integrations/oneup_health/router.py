from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.oneup_health.api import retrieve_token
from apps.integrations.oneup_health.domain import OneupHealthToken
from apps.shared.domain import Response
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/integrations/oneup_health", tags=["oneup_health"])

router.get(
    "/subject/{subject_id}/token",
    description="This endpoint is used to retrieve 1UpHealth API access token",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[OneupHealthToken]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(retrieve_token)
