import json

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.logs.db.schemas import NotificationLogSchema
from apps.logs.domain import (
    NotificationLog,
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.logs.errors import NotificationLogAlreadyExist
from infrastructure.database.crud import BaseCRUD

__all__ = ["NotificationLogCRUD"]


class NotificationLogCRUD(BaseCRUD[NotificationLogSchema]):
    schema_class = NotificationLogSchema

    async def all(
        self, query_set: NotificationLogQuery
    ) -> list[PublicNotificationLog]:
        """Return all notification logs where the user and device exists."""
        query: Query = (
            select(self.schema_class)
            .where(
                self.schema_class.user_id == query_set.user_id
                and self.schema_class.device_id == query_set.device_id
            )
            .order_by(self.schema_class.created_at.desc())
        )
        if query_set.limit:
            query = query.limit(query_set.limit)

        result: Result = await self._execute(query)
        results: list[PublicNotificationLog] = result.scalars().all()

        return [PublicNotificationLog.from_orm(log) for log in results]

    async def save(
        self, schema: NotificationLogCreate
    ) -> PublicNotificationLog:
        """Return notification log instance and the created information."""

        notif_desc_upd = True
        notif_in_queue_upd = True
        sched_notif_upd = True

        logs = await self.all(
            NotificationLogQuery(
                user_id=schema.user_id,
                device_id=schema.device_id,
                limit=1,
            )
        )

        previous = dict()
        if logs:
            previous = logs[0].dict()

        if not schema.notification_descriptions:
            schema.notification_descriptions = previous.get(
                "notification_descriptions", json.dumps(None)
            )
            notif_desc_upd = False

        if not schema.notification_in_queue:
            schema.notification_in_queue = previous.get(
                "notifications_in_queue", json.dumps(None)
            )
            notif_in_queue_upd = False

        if not schema.scheduled_notifications:
            schema.scheduled_notifications = previous.get(
                "scheduled_notifications", json.dumps(None)
            )
            sched_notif_upd = False

        # Save notification logs into the database
        try:

            instance: NotificationLogSchema = await self._create(
                NotificationLogSchema(
                    **schema.dict(),
                    notif_desc_updated=notif_desc_upd,
                    notif_in_queue_updated=notif_in_queue_upd,
                    sched_notif_updated=sched_notif_upd,
                )
            )
        except IntegrityError:
            raise NotificationLogAlreadyExist()

        # Create internal data model
        notification_log: PublicNotificationLog = (
            PublicNotificationLog.from_orm(instance)
        )

        return notification_log
