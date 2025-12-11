import uuid

from pydantic import parse_obj_as
from sqlalchemy import distinct, false, select, update
from sqlalchemy.orm import Query, joinedload

from apps.activities.db.schemas import ActivityHistorySchema
from apps.activities.domain import ActivityHistory, ActivityHistoryFull
from apps.activities.errors import ActivityHistoryDoeNotExist
from apps.applets.db.schemas import AppletHistorySchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityHistoriesCRUD"]


class ActivityHistoriesCRUD(BaseCRUD[ActivityHistorySchema]):
    schema_class = ActivityHistorySchema

    async def create_many(
        self,
        activities: list[ActivityHistorySchema],
    ) -> None:
        await self._create_many(activities)

    async def retrieve_by_applet_version(self, id_version) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id == id_version)
        query = query.order_by(ActivityHistorySchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_activities_by_applet_id_versions(self, id_versions: list[str]) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id.in_(id_versions))
        query = query.where(ActivityHistorySchema.is_reviewable == false())
        query = query.order_by(ActivityHistorySchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_by_applet_ids(self, applet_versions: list[str]) -> list[ActivityHistorySchema]:
        """
        retrieve activities by applet id_version fields
        order by id
        """
        query: Query = select(ActivityHistorySchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(AppletHistorySchema.id_version.in_(applet_versions))
        query = query.order_by(
            ActivityHistorySchema.id.asc(),
            ActivityHistorySchema.updated_at.asc(),
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_id(self, activity_id_version: str) -> ActivityHistorySchema:
        schema = await self._get("id_version", activity_id_version)
        if not schema:
            raise ActivityHistoryDoeNotExist()
        return schema

    async def exist_by_activity_id_or_raise(self, activity_id: uuid.UUID) -> None:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.id == activity_id)
        query = query.order_by(ActivityHistorySchema.created_at.asc())
        db_result = await self._execute(select(query.exists()))
        result = db_result.scalars().first()
        if not result:
            raise ActivityHistoryDoeNotExist()

    async def get_last_histories_by_applet(self, applet_id: uuid.UUID) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.where(ActivityHistorySchema.is_reviewable == false())
        query = query.order_by(
            ActivityHistorySchema.id.desc(),
            ActivityHistorySchema.created_at.desc(),
        )
        # For each activity get only last version
        query = query.distinct(ActivityHistorySchema.id)
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_applet_id_version(self, applet_id_version: str, non_performance=False) -> ActivityHistorySchema:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id == applet_id_version)
        query = query.where(ActivityHistorySchema.is_reviewable == false())
        if non_performance:
            query = query.where(ActivityHistorySchema.is_performance_task == false())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_activities(self, activity_id: uuid.UUID, versions: list[str] | None) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        if versions:
            query = query.where(AppletHistorySchema.version.in_(versions))

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_activity_id_versions_for_report(self, applet_id_version: str) -> list[str]:
        """Return list of available id_version of activities for report.
        Performance tasks are not used in PDF reports. So we should not send
        answers on performance task to the report server because decryption
        takes much time and CPU time is wasted on report server.
        """
        query: Query = select(distinct(ActivityHistorySchema.id_version))
        query = query.where(
            ActivityHistorySchema.applet_id == applet_id_version,
            ActivityHistorySchema.is_performance_task == false(),
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def update_by_id(self, id_, **values) -> None:
        subquery: Query = select(ActivityHistorySchema.id_version)
        subquery = subquery.where(ActivityHistorySchema.id == id_)
        subquery = subquery.limit(1)
        subquery = subquery.order_by(ActivityHistorySchema.created_at.desc())
        subquery = subquery.subquery()

        query = update(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.id_version.in_(select([subquery])))
        query = query.values(**values)
        query = query.returning(ActivityHistorySchema)
        await self._execute(query)

    async def load_full(self, id_versions: list[str]) -> list[ActivityHistoryFull]:
        if not id_versions:
            return []

        query = (
            select(ActivityHistorySchema)
            .options(joinedload(ActivityHistorySchema.items, innerjoin=True))
            .where(ActivityHistorySchema.id_version.in_(id_versions))
        )
        res = await self._execute(query)
        data = res.unique().scalars().all()

        return parse_obj_as(list[ActivityHistoryFull], data)

    async def get_by_history_ids(self, activity_history_ids: list[str]) -> list[ActivityHistory]:
        query: Query = (
            select(ActivityHistorySchema)
            .where(ActivityHistorySchema.id_version.in_(activity_history_ids))
            .order_by(ActivityHistorySchema.applet_id, ActivityHistorySchema.order)
        )
        res = await self._execute(query)
        activities: list[ActivityHistorySchema] = res.scalars().all()

        return parse_obj_as(list[ActivityHistory], activities)
