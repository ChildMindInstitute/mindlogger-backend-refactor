import uuid

from sqlalchemy import any_, exists, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activities.domain.response_type_config import (
    PerformanceTaskType,
    ResponseType,
)
from apps.activities.errors import ActivityHistoryDoeNotExist
from apps.applets.db.schemas import AppletHistorySchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityHistoriesCRUD"]


class ActivityHistoriesCRUD(BaseCRUD[ActivityHistorySchema]):
    schema_class = ActivityHistorySchema

    async def create_many(
        self,
        activities: list[ActivityHistorySchema],
    ):
        await self._create_many(activities)

    async def retrieve_by_applet_version(
        self, id_version
    ) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id == id_version)
        query = query.order_by(ActivityHistorySchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_activities_by_applet_version(
        self, id_version
    ) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id == id_version)
        query = query.where(
            ActivityHistorySchema.is_reviewable == False  # noqa: E712
        )
        query = query.order_by(ActivityHistorySchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_by_applet_ids(
        self, applet_versions: list[str]
    ) -> list[ActivityHistorySchema]:
        """
        retrieve activities by applet id_version fields
        order by id
        """
        query: Query = select(ActivityHistorySchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(
            AppletHistorySchema.id_version.in_(applet_versions)
        )
        query = query.order_by(
            ActivityHistorySchema.id.asc(),
            ActivityHistorySchema.updated_at.asc(),
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_id(
        self, activity_id_version: str
    ) -> ActivityHistorySchema:
        schema = await self._get("id_version", activity_id_version)
        if not schema:
            raise ActivityHistoryDoeNotExist()
        return schema

    async def exist_by_activity_id_or_raise(self, activity_id: uuid.UUID):
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.id == activity_id)
        query = query.order_by(ActivityHistorySchema.created_at.asc())
        db_result = await self._execute(select(query.exists()))
        result = db_result.scalars().first()
        if not result:
            raise ActivityHistoryDoeNotExist()

    async def get_by_ids(
        self, activity_id_versions: list[str]
    ) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(
            ActivityHistorySchema.id_version.in_(activity_id_versions)
        )
        query = query.order_by(ActivityHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_applet_assessment(
        self, applet_id_version: str
    ) -> ActivityHistorySchema:
        query: Query = select(ActivityHistorySchema)
        query = query.where(
            ActivityHistorySchema.applet_id == applet_id_version
        )
        query = query.order_by(ActivityHistorySchema.order.asc())
        query = query.limit(1)

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_reviewable_activities(
        self, applet_id_versions: list[str]
    ) -> list[ActivityHistorySchema]:
        if not applet_id_versions:
            return []

        query: Query = (
            select(ActivityHistorySchema)
            .where(
                ActivityHistorySchema.applet_id == any_(applet_id_versions),
                ActivityHistorySchema.is_reviewable.is_(True),
            )
            .order_by(
                ActivityHistorySchema.applet_id, ActivityHistorySchema.order
            )
            .distinct(ActivityHistorySchema.applet_id)
        )  # single activity per applet version

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_applet_id_for_summary(
        self,
        applet_id: uuid.UUID,
        applet_id_version: str | None = None,
    ) -> list[ActivityHistorySchema]:
        activity_types_query: Query = select(ActivityItemHistorySchema.id)
        activity_types_query = activity_types_query.where(
            ActivityItemHistorySchema.response_type.in_(
                [
                    PerformanceTaskType.FLANKER,
                    PerformanceTaskType.GYROSCOPE,
                    PerformanceTaskType.TOUCH,
                    PerformanceTaskType.ABTRAILS,
                    ResponseType.STABILITYTRACKER,
                ]
            )
        )
        activity_types_query = activity_types_query.where(
            ActivityItemHistorySchema.activity_id
            == ActivityHistorySchema.id_version
        )

        query: Query = select(
            ActivityHistorySchema,
            exists(activity_types_query).label("is_performance"),
        )
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        if applet_id_version:
            query = query.where(
                ActivityHistorySchema.applet_id == applet_id_version
            )
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.where(
            ActivityHistorySchema.is_reviewable == False  # noqa
        )
        query = query.order_by(
            ActivityHistorySchema.id.desc(),
            ActivityHistorySchema.created_at.desc(),
        )
        query = query.distinct(ActivityHistorySchema.id)
        db_result = await self._execute(query)
        schemas = []
        for activity_history_schema, is_performance in db_result.all():
            activity_history_schema.is_performance_task = is_performance
            schemas.append(activity_history_schema)

        return schemas

    async def get_by_applet_id_version(
        self, applet_id_version: str
    ) -> ActivityHistorySchema:
        query: Query = select(ActivityHistorySchema)
        query = query.where(
            ActivityHistorySchema.applet_id == applet_id_version
        )
        query = query.where(
            ActivityHistorySchema.is_reviewable == False  # noqa
        )
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_activities(
        self, activity_id: uuid.UUID, versions: list[str] | None
    ):
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
