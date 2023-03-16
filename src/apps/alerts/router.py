from fastapi.routing import APIRouter
from starlette import status

from apps.alerts.api.alert_config import alert_config_create
from apps.alerts.domain.alert_config import AlertsConfigCreateResponse
from apps.shared.domain import Response
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Alerts configuration create
router.post(
    "/config",
    description="""This endpoint using for adding new configuration
                for alert notified""",
    response_model_by_alias=True,
    response_model=Response[AlertsConfigCreateResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": Response[AlertsConfigCreateResponse]
        },
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(alert_config_create)
