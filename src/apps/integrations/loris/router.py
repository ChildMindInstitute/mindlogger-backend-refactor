from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import Response
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.integrations.loris.api import (
    send_applet_data_to_loris,
)


router = APIRouter(
    prefix="/integrations/loris", tags=["Integrations", "Loris"]
)


router.post(
    "/{applet_id}/data",
    description="""This endpoint is used to retrieve unencrypted applet data""",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(send_applet_data_to_loris)
