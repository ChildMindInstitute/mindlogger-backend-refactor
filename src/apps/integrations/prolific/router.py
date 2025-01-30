from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.prolific.api import get_public_prolific_integration, get_study_completion_codes
from apps.integrations.prolific.domain import ProlificCompletionCodeList, PublicProlificIntegration
from apps.shared.domain.response.errors import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/integrations/prolific", tags=["Prolific"])

router.get(
    "/applet/{applet_id}/study_id/{study_id}",
    description="This endpoint is used to get the prolific configuration for an applet",
    response_model=None,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": PublicProlificIntegration},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_public_prolific_integration)

router.get(
    "/applet/{applet_id}/completion_codes/{study_id}",
    description="This endpoint is used to get the list of completion codes for a given study",
    response_model=None,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ProlificCompletionCodeList},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_study_completion_codes)
