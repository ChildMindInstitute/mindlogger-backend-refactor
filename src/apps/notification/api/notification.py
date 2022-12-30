from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.notification.crud.notification import NotificationLogCRUD
from apps.notification.domain import (
    NotificationLog,
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.shared.domain import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


async def create_log(
    schema: NotificationLogCreate = Body(...),
) -> Response[PublicNotificationLog]:
    """Creates a new notification log."""
    notification_log: PublicNotificationLog = await NotificationLogCRUD().save(
        schema=schema
    )

    return Response(result=PublicNotificationLog(**notification_log.dict()))


async def get_logs(
    query: NotificationLogQuery = Depends(NotificationLogQuery),
) -> ResponseMulti[PublicNotificationLog]:
    """Returns all notification logs where the current user and device exists."""

    notification_logs: list[
        PublicNotificationLog
    ] = await NotificationLogCRUD().all(query)

    return ResponseMulti(results=notification_logs)
