from fastapi import Body, Depends

from apps.logs.crud.notification import NotificationLogCRUD
from apps.logs.domain import (
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.shared.domain import Response, ResponseMulti
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def notification_log_create(
    schema: NotificationLogCreate = Body(...),
    session=Depends(get_session),
) -> Response[PublicNotificationLog]:
    """Creates a new NotificationLog."""
    async with atomic(session):
        notification_log = await NotificationLogCRUD(session).save(
            schema=schema
        )

    return Response(result=notification_log)


async def notification_log_retrieve(
    query: NotificationLogQuery = Depends(NotificationLogQuery),
    session=Depends(get_session),
) -> ResponseMulti[PublicNotificationLog]:
    """Returns NotificationLogs of user and device"""
    async with atomic(session):
        notification_logs = await NotificationLogCRUD(session).filter(query)

    return ResponseMulti(result=notification_logs)
