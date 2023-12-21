from fastapi import Body, Depends

from apps.logs.crud.notification import NotificationLogCRUD
from apps.logs.domain import (
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.shared.domain import Response, ResponseMulti
from apps.users.services.user import UserService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def notification_log_create(
    schema: NotificationLogCreate = Body(...),
    session=Depends(get_session),
) -> Response[PublicNotificationLog]:
    """Creates a new NotificationLog."""
    async with atomic(session):
        # TODO: when mobile is ready for authentication, get data from
        # user.
        user = await UserService(session).get_by_email(schema.user_id)
        notification_log = await NotificationLogCRUD(session).save(
            schema=schema, user_id=str(user.id)
        )

    return Response(result=notification_log)


async def notification_log_retrieve(
    query: NotificationLogQuery = Depends(NotificationLogQuery),
    session=Depends(get_session),
) -> ResponseMulti[PublicNotificationLog]:
    """Returns NotificationLogs of user and device"""
    async with atomic(session):
        email = query.email if query.email else query.user_id
        user = await UserService(session).get_by_email(email)
        notification_logs = await NotificationLogCRUD(session).filter(
            query, user_id=str(user.id)
        )

    return ResponseMulti(
        result=notification_logs, count=len(notification_logs)
    )
