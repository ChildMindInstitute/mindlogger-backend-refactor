import uuid

from fastapi import Depends
from pydantic import parse_obj_as

from apps.alerts.domain import AlertPublic, AlertResponseMulti
from apps.alerts.service import AlertService
from apps.authentication.deps import get_current_user
from apps.shared.query_params import (
    BaseQueryParams,
    QueryParams,
    parse_query_params,
)
from apps.users.domain import User
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def get_all_alerts(
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(BaseQueryParams)),
    session=Depends(get_session),
) -> AlertResponseMulti:
    async with atomic(session):
        service = AlertService(session, user.id)
        alerts = await service.get_all_alerts(query_params)
        counts = await service.get_all_alerts_count()

    return AlertResponseMulti(
        result=parse_obj_as(list[AlertPublic], alerts),
        count=counts["alerts_all"],
        not_watched=counts["alerts_not_watched"],
    )


async def update_alert_as_watched(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await AlertService(session, user.id).watch(alert_id)
