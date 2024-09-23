from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Query
from sqlalchemy.sql.operators import ColumnOperators

from apps.logs.db.schemas import NotificationLogSchema
from apps.logs.domain import NotificationLogCreate, NotificationLogQuery, PublicNotificationLog
from apps.logs.errors import NotificationLogError
from infrastructure.database.crud import BaseCRUD

__all__ = ["NotificationLogCRUD"]


class NotificationLogCRUD(BaseCRUD[NotificationLogSchema]):
    schema_class = NotificationLogSchema

    async def filter(self, query_set: NotificationLogQuery, user_id: str) -> list[PublicNotificationLog]:
        """Return all NotificationLogs where the user and device exists."""
        query: Query = (
            select(self.schema_class)
            .where(
                self.schema_class.device_id == query_set.device_id,
                self.schema_class.user_id == user_id,
            )
            .order_by(self.schema_class.created_at.desc())
            .limit(query_set.limit)
        )

        result = await self._execute(query)
        logs = result.scalars().all()

        return [PublicNotificationLog.from_orm(log) for log in logs]

    async def save(self, schema: NotificationLogCreate, user_id: str) -> PublicNotificationLog:
        """Return NotificationLog instance."""

        notif_desc_upd = True
        notif_in_queue_upd = True
        sched_notif_upd = True

        if schema.notification_descriptions is None:
            description = await self.get_previous_description(user_id, schema)
            schema.notification_descriptions = description if description is not None else None
            notif_desc_upd = False

        if schema.notification_in_queue is None:
            in_queue = await self.get_previous_in_queue(user_id, schema)
            schema.notification_in_queue = in_queue if in_queue is not None else None
            notif_in_queue_upd = False

        if schema.scheduled_notifications is None:
            scheduled = await self.get_previous_scheduled_notifications(user_id, schema)
            schema.scheduled_notifications = scheduled if scheduled is not None else None
            sched_notif_upd = False

        # Save NotificationLogs into the database
        try:
            instance: NotificationLogSchema = await self._create(
                NotificationLogSchema(
                    action_type=schema.action_type,
                    user_id=user_id,
                    device_id=schema.device_id,
                    notification_descriptions=schema.notification_descriptions,
                    notification_in_queue=schema.notification_in_queue,
                    scheduled_notifications=schema.scheduled_notifications,
                    notification_descriptions_updated=notif_desc_upd,
                    notifications_in_queue_updated=notif_in_queue_upd,
                    scheduled_notifications_updated=sched_notif_upd,
                )
            )
            notification_log = PublicNotificationLog.from_orm(instance)

            return notification_log
        except Exception:
            raise NotificationLogError()

    async def _get_previous(
        self,
        user_id: str,
        device_id: str,
        field: InstrumentedAttribute,
        flt: list[ColumnOperators],
    ) -> NotificationLogSchema | None:
        query: Query = select(field)
        query = query.where(
            NotificationLogSchema.user_id == user_id,
            NotificationLogSchema.device_id == device_id,
            *flt,
        )
        query = query.order_by(NotificationLogSchema.created_at.desc())
        query = query.limit(1)
        res = await self._execute(query)
        return res.scalars().one_or_none()

    async def get_previous_description(
        self, user_id: str, schema: NotificationLogCreate
    ) -> NotificationLogSchema | None:
        return await self._get_previous(
            user_id,
            schema.device_id,
            NotificationLogSchema.notification_descriptions,
            [NotificationLogSchema.notification_descriptions.isnot(None)],
        )

    async def get_previous_in_queue(self, user_id: str, schema: NotificationLogCreate) -> NotificationLogSchema | None:
        return await self._get_previous(
            user_id,
            schema.device_id,
            NotificationLogSchema.notification_in_queue,
            [NotificationLogSchema.notification_in_queue.isnot(None)],
        )

    async def get_previous_scheduled_notifications(
        self, user_id: str, schema: NotificationLogCreate
    ) -> NotificationLogSchema | None:
        return await self._get_previous(
            user_id,
            schema.device_id,
            NotificationLogSchema.scheduled_notifications,
            [NotificationLogSchema.scheduled_notifications.isnot(None)],
        )
