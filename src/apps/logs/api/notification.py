from fastapi import Body, Depends

from apps.logs.crud.notification import NotificationLogCRUD
from apps.logs.domain import (
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.shared.domain import Response, ResponseMulti


async def create_notification_log(
    schema: NotificationLogCreate = Body(...),
) -> Response[PublicNotificationLog]:
    """Creates a new NotificationLog."""
    notification_log: PublicNotificationLog = await NotificationLogCRUD().save(
        schema=schema
    )

    return Response(result=notification_log)


async def get_notification_logs(
    query: NotificationLogQuery = Depends(NotificationLogQuery),
) -> ResponseMulti[PublicNotificationLog]:
    """Returns NotificationLogs of user and device"""

    notification_logs: list[
        PublicNotificationLog
    ] = await NotificationLogCRUD().filter(query)

    return ResponseMulti(results=notification_logs)
