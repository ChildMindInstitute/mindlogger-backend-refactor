__all__ = ["ScheduleHistoryCRUD", "AppletEventsCRUD", "NotificationHistoryCRUD", "ReminderHistoryCRUD"]

import asyncio
import uuid

from sqlalchemy import update

from apps.schedule.db.schemas import (
    AppletEventsSchema,
    EventHistorySchema,
    NotificationHistorySchema,
    ReminderHistorySchema,
)
from infrastructure.database import BaseCRUD


class ScheduleHistoryCRUD(BaseCRUD[EventHistorySchema]):
    async def add(self, event: EventHistorySchema) -> EventHistorySchema:
        return await self._create(event)

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]):
        id_versions = [f"{event[0]}_{event[1]}" for event in events]

        query = update(EventHistorySchema).where(EventHistorySchema.id_version.in_(id_versions)).values(is_deleted=True)

        await self._execute(query)

        await asyncio.gather(
            AppletEventsCRUD(self.session).mark_as_deleted(events),
            NotificationHistoryCRUD(self.session).mark_as_deleted(events),
            ReminderHistoryCRUD(self.session).mark_as_deleted(events)
        )


class AppletEventsCRUD(BaseCRUD[AppletEventsSchema]):
    async def add(self, applet_event: AppletEventsSchema) -> AppletEventsSchema:
        return await self._create(applet_event)

    async def add_many(self, applet_events: list[AppletEventsSchema]) -> list[AppletEventsSchema]:
        return await self._create_many(applet_events)

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]):
        id_versions = [f"{event[0]}_{event[1]}" for event in events]

        query = update(AppletEventsSchema).where(AppletEventsSchema.event_id.in_(id_versions)).values(is_deleted=True)

        await self._execute(query)


class NotificationHistoryCRUD(BaseCRUD[NotificationHistorySchema]):
    async def add(self, notification: NotificationHistorySchema) -> NotificationHistorySchema:
        return await self._create(notification)

    async def add_many(self, notifications: list[NotificationHistorySchema]) -> list[NotificationHistorySchema]:
        return await self._create_many(notifications)

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]):
        id_versions = [f"{event[0]}_{event[1]}" for event in events]

        query = (
            update(NotificationHistorySchema)
            .where(NotificationHistorySchema.event_id.in_(id_versions))
            .values(is_deleted=True)
        )

        await self._execute(query)


class ReminderHistoryCRUD(BaseCRUD[ReminderHistorySchema]):
    async def add(self, reminder: ReminderHistorySchema) -> ReminderHistorySchema:
        return await self._create(reminder)

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]):
        id_versions = [f"{event[0]}_{event[1]}" for event in events]

        query = (
            update(ReminderHistorySchema).where(ReminderHistorySchema.event_id.in_(id_versions)).values(is_deleted=True)
        )

        await self._execute(query)
