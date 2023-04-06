import uuid

from sqlalchemy.orm import Query
from sqlalchemy.sql import select, delete, update
from apps.schedule.db.schemas import NotificationSchema, ReminderSchema
from apps.schedule.domain.schedule.internal import (
    NotificationSettingCreate,
    NotificationSetting,
    ReminderSettingCreate,
    ReminderSetting,
)
from apps.schedule.domain.schedule.public import (
    PublicNotificationSetting,
    PublicReminderSetting,
)
from apps.schedule.errors import (
    UserEventAlreadyExists,
)
from infrastructure.database import BaseCRUD

__all__ = [
    "NotificationCRUD",
]


class NotificationCRUD(BaseCRUD[NotificationSchema]):
    schema_class = NotificationSchema

    async def create_many(
        self,
        notifications: list[NotificationSchema],
    ):
        result = await self._create_many(notifications)
        return result

    async def get_all_by_event_id(
        self, event_id: uuid.UUID
    ) -> list[NotificationSetting]:
        """Return all notifications by event id."""

        query: Query = select(NotificationSchema)
        query = query.where(NotificationSchema.event_id == event_id)
        query = query.order_by(NotificationSchema.id.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def delete_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all notifications by event id."""
        query: Query = update(NotificationSchema)
        query = query.where(NotificationSchema.event_id.in_(event_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)


class ReminderCRUD(BaseCRUD[ReminderSchema]):
    schema_class = ReminderSchema

    async def create(self, reminder: ReminderSettingCreate) -> ReminderSetting:
        """Create a reminder."""

        db_reminder = await self._create(ReminderSchema(**reminder.dict()))
        return ReminderSetting.from_orm(db_reminder)

    async def get_by_event_id(self, event_id: uuid.UUID) -> ReminderSetting:
        """Return all reminders by event id."""

        query: Query = select(ReminderSchema)
        query = query.where(ReminderSchema.event_id == event_id)
        query = query.order_by(ReminderSchema.id.asc())
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def delete_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all reminders by event id."""
        query: Query = update(ReminderSchema)
        query = query.where(ReminderSchema.event_id.in_(event_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def update(self, schema: ReminderSettingCreate) -> ReminderSetting:
        """Update reminder instance."""
        instance = await self._update_one(
            lookup="event_id",
            value=schema.event_id,
            schema=ReminderSchema(**schema.dict()),
        )
        return ReminderSetting.from_orm(instance)
