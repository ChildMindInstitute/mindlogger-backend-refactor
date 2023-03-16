from fastapi import Body, Depends

from apps.alerts.domain.alert_config import AlertsConfigCreateRequest
from apps.authentication.deps import get_current_user
from apps.users.domain import User


async def alert_config_create(
    user: User = Depends(get_current_user),
    schema: AlertsConfigCreateRequest = Body(...),
):
    pass
