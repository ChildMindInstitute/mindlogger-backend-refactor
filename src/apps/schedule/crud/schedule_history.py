__all__ = ["ScheduleHistoryCRUD", "AppletEventsCRUD", "NotificationHistoryCRUD", "ReminderHistoryCRUD"]

import asyncio
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Query
from sqlalchemy.sql import func

from apps.activities.db.schemas import ActivityHistorySchema
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.applets.db.schemas import AppletHistorySchema
from apps.schedule.db.schemas import (
    AppletEventsSchema,
    EventHistorySchema,
    NotificationHistorySchema,
    ReminderHistorySchema,
)
from apps.schedule.domain.schedule.public import ExportEventHistoryDto
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.query_params import QueryParams
from infrastructure.database import BaseCRUD


class _ScheduleHistoryExportFilters(Filtering):
    respondent_ids = FilterField(EventHistorySchema.user_id, method_name="filter_respondent_ids")
    from_date = FilterField(EventHistorySchema.created_at, Comparisons.GREAT_OR_EQUAL)
    to_date = FilterField(EventHistorySchema.created_at, Comparisons.LESS_OR_EQUAL)

    def filter_respondent_ids(self, field, value):
        return or_(field.in_(value), EventHistorySchema.user_id.is_(None))


class ScheduleHistoryCRUD(BaseCRUD[EventHistorySchema]):
    schema_class = EventHistorySchema

    async def get_by_id(self, id_version: str) -> EventHistorySchema | None:
        return await self._get("id_version", id_version)

    async def add(self, event: EventHistorySchema) -> EventHistorySchema:
        return await self._create(event)

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]):
        id_versions = [f"{event[0]}_{event[1]}" for event in events]

        query = update(EventHistorySchema).where(EventHistorySchema.id_version.in_(id_versions)).values(is_deleted=True)

        await self._execute(query)

        await asyncio.gather(
            AppletEventsCRUD(self.session).mark_as_deleted(events),
            NotificationHistoryCRUD(self.session).mark_as_deleted(events),
            ReminderHistoryCRUD(self.session).mark_as_deleted(events),
        )

    async def retrieve_applet_all_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportEventHistoryDto], int]:
        query: Query = select(
            AppletHistorySchema.id.label('applet_id'),
            AppletHistorySchema.version.label('applet_version'),
            AppletHistorySchema.display_name.label('applet_name'),
            EventHistorySchema.user_id,
            EventHistorySchema.id.label('event_id'),
            EventHistorySchema.event_type,
            EventHistorySchema.version.label('event_version'),
            EventHistorySchema.created_at.label('event_version_created_at'),
            AppletHistorySchema.created_at.label('linked_with_applet_at'),
            EventHistorySchema.updated_by.label('event_updated_by'),
            func.coalesce(
                EventHistorySchema.activity_flow_id, EventHistorySchema.activity_id
            ).label('activity_or_flow_id'),
            func.coalesce(
                ActivityFlowHistoriesSchema.name, ActivityHistorySchema.name
            ).label('activity_or_flow_name'),
            EventHistorySchema.periodicity,
            EventHistorySchema.start_date,
            EventHistorySchema.start_time,
            EventHistorySchema.end_date,
            EventHistorySchema.end_time,
            EventHistorySchema.selected_date,
        )
        query = query.select_from(EventHistorySchema)
        query = query.join(
            AppletEventsSchema,
            EventHistorySchema.id_version == AppletEventsSchema.event_id,
        )
        query = query.join(
            AppletHistorySchema,
            AppletEventsSchema.applet_id == AppletHistorySchema.id_version,
        )
        query = query.outerjoin(
            ActivityHistorySchema,
            EventHistorySchema.activity_id == ActivityHistorySchema.id,
        )
        query = query.outerjoin(
            ActivityFlowHistoriesSchema,
            EventHistorySchema.activity_flow_id == ActivityFlowHistoriesSchema.id,
        )
        query = query.where(AppletHistorySchema.id == applet_id)

        _filters = _ScheduleHistoryExportFilters().get_clauses(**query_params.filters)
        if _filters:
            query = query.where(*_filters)

        query = query.order_by(EventHistorySchema.created_at, AppletEventsSchema.created_at)

        result = await self._execute(query)

        # TODO: Implement pagination
        return [ExportEventHistoryDto(**row) for row in result], 0


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
