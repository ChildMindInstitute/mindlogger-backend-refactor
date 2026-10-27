from fastapi.routing import APIRouter
from starlette import status

from apps.legal.api import msa_version_get
from apps.legal.domain import MsaVersion
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE, Response

router = APIRouter(prefix="/legal", tags=["Legal"])

router.get(
    "/msa",
    response_model=Response[MsaVersion],
    responses={
        status.HTTP_200_OK: {"model": Response[MsaVersion]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(msa_version_get)
