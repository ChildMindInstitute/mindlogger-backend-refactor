__all__ = ["ScheduleHistoryCRUD", "AppletEventsCRUD", "NotificationHistoryCRUD", "ReminderHistoryCRUD"]

import asyncio
import datetime
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_, func

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
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.subjects.db.schemas import SubjectSchema
from infrastructure.database import BaseCRUD


class _ScheduleHistoryExportFilters(Filtering):
    respondent_ids = FilterField(EventHistorySchema.user_id, method_name="filter_nullable_ids")
    subject_ids = FilterField(SubjectSchema.id, method_name="filter_nullable_ids")
    activity_or_flow_ids = FilterField(
        func.coalesce(EventHistorySchema.activity_flow_id, EventHistorySchema.activity_id), Comparisons.IN
    )

    def filter_nullable_ids(self, field, value):
        return or_(field.in_(value), field.is_(None))


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
        columns = [
            AppletHistorySchema.id.label("applet_id"),
            AppletHistorySchema.version.label("applet_version"),
            AppletHistorySchema.display_name.label("applet_name"),
            EventHistorySchema.user_id,
            SubjectSchema.id.label("subject_id"),
            EventHistorySchema.id.label("event_id"),
            EventHistorySchema.event_type,
            EventHistorySchema.version.label("event_version"),
            EventHistorySchema.created_at.label("event_version_created_at"),
            EventHistorySchema.updated_at.label("event_version_updated_at"),
            EventHistorySchema.is_deleted.label("event_version_is_deleted"),
            AppletEventsSchema.created_at.label("linked_with_applet_at"),
            EventHistorySchema.updated_by.label("event_updated_by"),
            func.coalesce(EventHistorySchema.activity_flow_id, EventHistorySchema.activity_id).label(
                "activity_or_flow_id"
            ),
            func.coalesce(ActivityFlowHistoriesSchema.name, ActivityHistorySchema.name).label("activity_or_flow_name"),
            func.coalesce(ActivityFlowHistoriesSchema.is_hidden, ActivityHistorySchema.is_hidden).label(
                "activity_or_flow_hidden"
            ),
            EventHistorySchema.access_before_schedule,
            EventHistorySchema.one_time_completion,
            EventHistorySchema.periodicity,
            EventHistorySchema.start_date,
            func.coalesce(EventHistorySchema.start_time, datetime.time(0, 0, 0)).label("start_time"),
            EventHistorySchema.end_date,
            func.coalesce(EventHistorySchema.end_time, datetime.time(23, 59, 0)).label("end_time"),
            EventHistorySchema.selected_date,
        ]

        query: Query = select(*columns)
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
            SubjectSchema,
            and_(
                EventHistorySchema.user_id == SubjectSchema.user_id,
                AppletHistorySchema.id == SubjectSchema.applet_id,
            ),
        )
        query = query.outerjoin(
            ActivityHistorySchema,
            and_(
                EventHistorySchema.activity_id == ActivityHistorySchema.id,
                AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
            ),
        )
        query = query.outerjoin(
            ActivityFlowHistoriesSchema,
            and_(
                EventHistorySchema.activity_flow_id == ActivityFlowHistoriesSchema.id,
                AppletHistorySchema.id_version == ActivityFlowHistoriesSchema.applet_id,
            ),
        )
        query = query.where(AppletHistorySchema.id == applet_id)

        _filters = _ScheduleHistoryExportFilters().get_clauses(**query_params.filters)
        if _filters:
            query = query.where(*_filters)

        unlabeled_columns = [col.element if hasattr(col, "element") else col for col in columns]

        query = query.group_by(*unlabeled_columns, EventHistorySchema.start_time, EventHistorySchema.end_time)
        query = query.order_by(EventHistorySchema.created_at, AppletEventsSchema.created_at)

        query_count: Query = select(func.count()).select_from(query.with_only_columns(*unlabeled_columns).subquery())

        query = paging(query, query_params.page, query_params.limit)

        coro_data, coro_count = (
            self._execute(query),
            self._execute(query_count),
        )

        res, res_count = await asyncio.gather(coro_data, coro_count)

        data = [ExportEventHistoryDto(**row) for row in res]
        total = res_count.scalars().one()

        return data, total


class AppletEventsCRUD(BaseCRUD[AppletEventsSchema]):
    async def find_by_applet_id_version(self, applet_id_version: str) -> list[AppletEventsSchema]:
        query = select(AppletEventsSchema)
        query = query.where(
            AppletEventsSchema.applet_id == applet_id_version,
            AppletEventsSchema.soft_exists(),
        )

        res = await self._execute(query)

        return res.scalars().all()

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
