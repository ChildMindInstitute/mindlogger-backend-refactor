from fastapi.routing import APIRouter
from starlette import status

from apps.logs.api.notification import (
    notification_log_create,
    notification_log_retrieve,
)
from apps.logs.domain import PublicNotificationLog
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)

router = APIRouter(prefix="/logs", tags=["Logs"])

router.get(
    "/notification",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicNotificationLog],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicNotificationLog]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(notification_log_retrieve)

router.post(
    "/notification",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[PublicNotificationLog],
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicNotificationLog]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(notification_log_create)
