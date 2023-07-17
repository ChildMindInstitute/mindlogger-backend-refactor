from fastapi.routing import APIRouter
from starlette import status

from apps.alerts.api import get_all_alerts, update_alert_as_watched
from apps.alerts.domain import AlertPublic
from apps.shared.domain import ResponseMulti
from apps.shared.domain.response import DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/alerts", tags=["Alerts"])

router.get(
    "",
    description="This endpoint using for get all alerts for specific",
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AlertPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(get_all_alerts)

router.post(
    "/{alert_id}/is_watched",
    description="""This endpoint using for update alert status
                at is_watched true""",
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(update_alert_as_watched)
