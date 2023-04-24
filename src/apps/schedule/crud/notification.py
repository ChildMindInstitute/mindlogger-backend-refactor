import uuid

from sqlalchemy.orm import Query
from sqlalchemy.sql import delete, select, update

from apps.schedule.db.schemas import NotificationSchema, ReminderSchema
from apps.schedule.domain.schedule.internal import (
    NotificationSetting,
    ReminderSetting,
    ReminderSettingCreate,
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
    ) -> list[NotificationSetting]:
        result = await self._create_many(notifications)
        return [
            NotificationSetting.from_orm(notification)
            for notification in result
        ]

    async def get_all_by_event_id(
        self, event_id: uuid.UUID
    ) -> list[NotificationSetting]:
        """Return all notifications by event id."""

        query: Query = select(NotificationSchema)
        query = query.where(NotificationSchema.event_id == event_id)
        query = query.order_by(NotificationSchema.id.asc())
        db_result = await self._execute(query)
        result = db_result.scalars().all()

        return [
            NotificationSetting.from_orm(notification)
            for notification in result
        ]

    async def delete_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all notifications by event id."""
        query: Query = delete(NotificationSchema)
        query = query.where(NotificationSchema.event_id.in_(event_ids))
        await self._execute(query)


class ReminderCRUD(BaseCRUD[ReminderSchema]):
    schema_class = ReminderSchema

    async def create(self, reminder: ReminderSettingCreate) -> ReminderSetting:
        """Create a reminder."""

        db_reminder = await self._create(ReminderSchema(**reminder.dict()))
        return ReminderSetting.from_orm(db_reminder)

    async def get_by_event_id(self, event_id: uuid.UUID) -> ReminderSchema:
        """Return all reminders by event id."""

        query: Query = select(ReminderSchema)
        query = query.where(ReminderSchema.event_id == event_id)
        query = query.order_by(ReminderSchema.id.asc())
        db_result = await self._execute(query)

        return db_result.scalars().first()

    async def delete_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all reminders by event id."""
        query: Query = delete(ReminderSchema)
        query = query.where(ReminderSchema.event_id.in_(event_ids))
        await self._execute(query)

    async def update(self, schema: ReminderSettingCreate) -> ReminderSetting:
        """Update reminder instance."""
        query: Query = update(ReminderSchema)
        query = query.where(ReminderSchema.event_id == schema.event_id)
        query = query.values(**schema.dict(exclude={"event_id"}))
        query = query.returning(self.schema_class)
        db_result = await self._execute(query)
        result = db_result.scalars().first()
        return ReminderSetting.from_orm(result)
