from fastapi.routing import APIRouter
from starlette import status

from apps.legal.api import msa_accept, msa_status_get, msa_version_get
from apps.legal.domain import MsaVersion, PublicMsaStatus
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE, Response

router = APIRouter(prefix="/legal", tags=["Legal"])

router.get(
    "/msa",
    response_model=Response[MsaVersion],
    responses={
        status.HTTP_200_OK: {"model": Response[MsaVersion]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(msa_version_get)

router.get(
    "/msa/status",
    response_model=Response[PublicMsaStatus],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicMsaStatus]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(msa_status_get)

router.post(
    "/msa/accept",
    response_model=Response[PublicMsaStatus],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicMsaStatus]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(msa_accept)
