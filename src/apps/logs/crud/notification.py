from typing import Any
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

__all__ = ["NotificationLogsCRUD"]


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
            query.limit(query_set.limit)

        result: Result = await self._execute(query)
        results: list[PublicNotificationLog] = result.scalars().all()

        return [NotificationLog.from_orm(log) for log in results]

    async def save(self, schema: NotificationLogCreate) -> NotificationLog:
        """Return notification log instance and the created information."""

        notification_descriptions_updated = True
        notifications_in_queue_updated = True
        scheduled_notifications_updated = True

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
            notification_descriptions_updated = False

        if not schema.notification_in_queue:
            schema.notification_in_queue = previous.get(
                "notifications_in_queue", json.dumps(None)
            )
            notifications_in_queue_updated = False

        if not schema.scheduled_notifications:
            schema.scheduled_notifications = previous.get(
                "scheduled_notifications", json.dumps(None)
            )
            scheduled_notifications_updated = False

        # Save notification logs into the database
        try:

            instance: NotificationLogSchema = await self._create(
                NotificationLogSchema(
                    **schema.dict(),
                    notification_descriptions_updated=notification_descriptions_updated,
                    notifications_in_queue_updated=notifications_in_queue_updated,
                    scheduled_notifications_updated=scheduled_notifications_updated,
                )
            )
        except IntegrityError:
            raise NotificationLogAlreadyExist()

        # Create internal data model
        notification_log: NotificationLog = NotificationLog.from_orm(instance)

        return notification_log
