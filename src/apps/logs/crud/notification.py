import json

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.logs.db.schemas import NotificationLogSchema
from apps.logs.domain import (
    NotificationLogCreate,
    NotificationLogQuery,
    PublicNotificationLog,
)
from apps.logs.errors import NotificationLogError
from infrastructure.database.crud import BaseCRUD

__all__ = ["NotificationLogCRUD"]


class NotificationLogCRUD(BaseCRUD[NotificationLogSchema]):
    schema_class = NotificationLogSchema

    async def filter(
        self, query_set: NotificationLogQuery
    ) -> list[PublicNotificationLog]:
        """Return all NotificationLogs where the user and device exists."""
        query: Query = (
            select(self.schema_class)
            .where(
                self.schema_class.user_id == query_set.user_id,
                self.schema_class.device_id == query_set.device_id,
            )
            .order_by(self.schema_class.created_at.desc())
            .limit(query_set.limit)
        )

        result = await self._execute(query)
        logs = result.scalars().all()

        return [PublicNotificationLog.from_orm(log) for log in logs]

    async def save(
        self, schema: NotificationLogCreate
    ) -> PublicNotificationLog:
        """Return NotificationLog instance."""

        notif_desc_upd = True
        notif_in_queue_upd = True
        sched_notif_upd = True

        previous = await self.get_previous(schema.user_id, schema.device_id)

        if not schema.notification_descriptions:
            schema.notification_descriptions = (
                json.dumps(previous.notification_descriptions)
                if previous
                else json.dumps(None)
            )
            notif_desc_upd = False

        if not schema.notification_in_queue:
            schema.notification_in_queue = (
                json.dumps(previous.notification_in_queue)
                if previous
                else json.dumps(None)
            )
            notif_in_queue_upd = False

        if not schema.scheduled_notifications:
            schema.scheduled_notifications = (
                json.dumps(previous.scheduled_notifications)
                if previous
                else json.dumps(None)
            )
            sched_notif_upd = False

        # Save NotificationLogs into the database
        try:
            instance: NotificationLogSchema = await self._create(
                NotificationLogSchema(
                    **schema.dict(),
                    notification_descriptions_updated=notif_desc_upd,
                    notifications_in_queue_updated=notif_in_queue_upd,
                    scheduled_notifications_updated=sched_notif_upd,
                )
            )
            notification_log = PublicNotificationLog.from_orm(instance)

            return notification_log
        except Exception:
            raise NotificationLogError()

    async def get_previous(
        self, user_id: str, device_id: str
    ) -> NotificationLogSchema | None:
        query: Query = select(NotificationLogSchema)
        query = query.where(
            NotificationLogSchema.user_id == user_id,
            NotificationLogSchema.device_id == device_id,
        )
        query = query.order_by(NotificationLogSchema.created_at.desc())
        query = query.limit(1)
        res = await self._execute(query)
        return res.scalars().one_or_none()
