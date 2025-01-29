__all__ = ["ScheduleHistoryCRUD", "AppletEventsCRUD", "NotificationHistoryCRUD", "ReminderHistoryCRUD"]

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


class AppletEventsCRUD(BaseCRUD[AppletEventsSchema]):
    async def add(self, applet_event: AppletEventsSchema) -> AppletEventsSchema:
        return await self._create(applet_event)


class NotificationHistoryCRUD(BaseCRUD[NotificationHistorySchema]):
    async def add(self, notification: NotificationHistorySchema) -> NotificationHistorySchema:
        return await self._create(notification)

    async def add_many(self, notifications: list[NotificationHistorySchema]) -> list[NotificationHistorySchema]:
        return await self._create_many(notifications)


class ReminderHistoryCRUD(BaseCRUD[ReminderHistorySchema]):
    async def add(self, reminder: ReminderHistorySchema) -> ReminderHistorySchema:
        return await self._create(reminder)
