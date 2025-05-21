__all__ = ["UserDeviceEventsHistoryCRUD"]

import asyncio
import datetime
import uuid

from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Query
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import and_, select

from apps.applets.db.schemas import AppletHistorySchema
from apps.schedule.db.schemas import AppletEventsSchema, EventHistorySchema, UserDeviceEventsHistorySchema
from apps.schedule.domain.schedule.public import ExportDeviceHistoryDto
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from infrastructure.database import BaseCRUD


class _UserDeviceEventsHistoryExportFilters(Filtering):
    respondent_ids = FilterField(UserDeviceEventsHistorySchema.user_id, Comparisons.IN)


class UserDeviceEventsHistoryCRUD(BaseCRUD[UserDeviceEventsHistorySchema]):
    def __init__(self, session):
        super().__init__(session)
        self.schema_class = UserDeviceEventsHistorySchema

    async def get_device(
        self,
        device_id: str,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_version: str,
    ) -> UserDeviceEventsHistorySchema:
        query: Query = select(UserDeviceEventsHistorySchema)
        query = query.where(UserDeviceEventsHistorySchema.device_id == device_id)
        query = query.where(UserDeviceEventsHistorySchema.user_id == user_id)
        query = query.where(UserDeviceEventsHistorySchema.event_id == event_id)
        query = query.where(UserDeviceEventsHistorySchema.event_version == event_version)

        result = await self._execute(query)
        return result.scalars().first()

    async def record_event_versions(
        self,
        user_id: uuid.UUID,
        device_id: str,
        event_versions: list[tuple[uuid.UUID, str]],
        os_name: str | None = None,
        os_version: str | None = None,
        app_version: str | None = None,
        time_zone: str | None = None,
    ) -> list[UserDeviceEventsHistorySchema]:
        values = [
            dict(
                user_id=user_id,
                device_id=device_id,
                event_id=event_id,
                event_version=event_version,
                os_name=os_name,
                os_version=os_version,
                app_version=app_version,
                time_zone=time_zone,
            )
            for event_id, event_version in event_versions
        ]

        upsert: Insert = pg_insert(UserDeviceEventsHistorySchema)
        upsert = upsert.values(values)
        upsert = upsert.on_conflict_do_update(
            constraint=UserDeviceEventsHistorySchema.unique_constraint,
            set_={
                "updated_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            },
        )
        upsert = upsert.returning(UserDeviceEventsHistorySchema)
        result = await self._execute(upsert)

        rows = result.mappings().all()
        model = [UserDeviceEventsHistorySchema(**row) for row in rows]

        return model

    async def get_all_by_device_id(self, device_id: str) -> list[UserDeviceEventsHistorySchema]:
        query: Query = select(UserDeviceEventsHistorySchema)
        query = query.where(UserDeviceEventsHistorySchema.device_id == device_id)
        result = await self._execute(query)
        return result.scalars().all()

    async def get_all(self) -> list[UserDeviceEventsHistorySchema]:
        return await self._all()

    async def retrieve_applet_all_device_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportDeviceHistoryDto], int]:
        columns = [
            UserDeviceEventsHistorySchema.user_id,
            UserDeviceEventsHistorySchema.device_id,
            UserDeviceEventsHistorySchema.event_id,
            UserDeviceEventsHistorySchema.event_version,
            EventHistorySchema.start_date,
            func.coalesce(EventHistorySchema.start_time, datetime.time(0, 0, 0)).label("start_time"),
            EventHistorySchema.end_date,
            func.coalesce(EventHistorySchema.end_time, datetime.time(23, 59, 0)).label("end_time"),
            EventHistorySchema.access_before_schedule,
            UserDeviceEventsHistorySchema.created_at,
            UserDeviceEventsHistorySchema.time_zone.label("user_time_zone"),
        ]

        query: Query = select(*columns)
        query = query.select_from(UserDeviceEventsHistorySchema)
        query = query.join(
            EventHistorySchema,
            and_(
                UserDeviceEventsHistorySchema.event_id == EventHistorySchema.id,
                UserDeviceEventsHistorySchema.event_version == EventHistorySchema.version,
            ),
        )
        query = query.join(
            AppletEventsSchema,
            EventHistorySchema.id_version == AppletEventsSchema.event_id,
        )
        query = query.join(
            AppletHistorySchema,
            AppletEventsSchema.applet_id == AppletHistorySchema.id_version,
        )
        query = query.where(AppletHistorySchema.id == applet_id)

        _filters = _UserDeviceEventsHistoryExportFilters().get_clauses(**query_params.filters)
        if _filters:
            query = query.where(*_filters)

        unlabeled_columns = [col.element if hasattr(col, "element") else col for col in columns]
        query = query.group_by(*unlabeled_columns, EventHistorySchema.start_time, EventHistorySchema.end_time)

        query = query.order_by(UserDeviceEventsHistorySchema.created_at)

        query_count: Query = select(func.count()).select_from(query.with_only_columns(*unlabeled_columns).subquery())

        query = paging(query, query_params.page, query_params.limit)

        coro_data, coro_count = (
            self._execute(query),
            self._execute(query_count),
        )

        res, res_count = await asyncio.gather(coro_data, coro_count)

        data = [ExportDeviceHistoryDto(**row) for row in res]
        total = res_count.scalars().one()

        return data, total
