from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.oneup_health.api import (
    refresh_token,
    retrieve_token,
    retrieve_token_by_submit_id,
    trigger_data_fetch,
)
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

router.get(
    "/applet/{applet_id}/submissions/{submit_id}/token",
    description="This endpoint is used to retrieve 1UpHealth API access token",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[OneupHealthToken]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(retrieve_token_by_submit_id)

router.post(
    "/refresh_token",
    description="This endpoint is used to refresh an expired 1UpHealth access token using a refresh token",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[OneupHealthToken]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(refresh_token)

router.get(
    "/applet/{applet_id}/submissions/{submit_id}/trigger_data_fetch",
    description="This endpoint is used to trigger 1UpHealth data fetch. Use only for test purposes, "
    "should not me called by frontend",
    status_code=status.HTTP_200_OK,
)(trigger_data_fetch)
