import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityHistorySchema, ActivityItemHistorySchema, ActivitySchema
from apps.applets.db.schemas import AppletHistorySchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityItemHistoriesCRUD"]


class ActivityItemHistoriesCRUD(BaseCRUD[ActivityItemHistorySchema]):
    schema_class = ActivityItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityItemHistorySchema],
    ):
        await self._create_many(items)

    async def retrieve_by_applet_version(self, id_version: str) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version == ActivityItemHistorySchema.activity_id,
        )
        query = query.filter(ActivityHistorySchema.applet_id == id_version)
        query = query.order_by(
            ActivityItemHistorySchema.order.asc(),
        )

        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_activity_id_version(self, activity_id: str) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(ActivityItemHistorySchema.activity_id == activity_id)
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_activity_id_versions(self, id_versions: list[str]) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(ActivityItemHistorySchema.activity_id.in_(id_versions))
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_applets_assessments(
        self,
        applet_id: uuid.UUID,
    ) -> list[ActivityItemHistorySchema]:
        subquery: Query = (
            select(ActivityHistorySchema.id_version)
            .join(ActivitySchema, ActivitySchema.id == ActivityHistorySchema.id)
            .where(
                ActivitySchema.is_reviewable.is_(True),
                ActivitySchema.applet_id == applet_id,
            )
            .order_by(ActivityHistorySchema.created_at.desc())
            .limit(1)
            .subquery()
        )

        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version == ActivityItemHistorySchema.activity_id,
        )
        query = query.join(ActivitySchema, ActivitySchema.id == ActivityHistorySchema.id)
        query = query.where(ActivitySchema.applet_id == applet_id)
        query = query.where(
            ActivityHistorySchema.is_reviewable == True,  # noqa: E712
            ActivityHistorySchema.id_version.in_(select(subquery)),
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)

        res = db_result.scalars().all()
        return res

    async def get_assessment_activity_items(self, id_version: str | None) -> list[ActivityItemHistorySchema | None]:
        if not id_version:
            return []  # pragma: no cover
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version == ActivityItemHistorySchema.activity_id,
        )
        query = query.join(ActivitySchema, ActivitySchema.id == ActivityHistorySchema.id)
        query = query.where(
            ActivityHistorySchema.is_reviewable == True,  # noqa: E712
            ActivityHistorySchema.id_version == id_version,
        )
        db_result = await self._execute(query)
        res = db_result.scalars().all()
        return res

    async def get_activity_items(
        self, activity_id: uuid.UUID, versions: list[str] | None
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version == ActivityItemHistorySchema.activity_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        if versions:
            query = query.join(
                AppletHistorySchema,
                AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
            )
            query = query.where(AppletHistorySchema.version.in_(versions))
        query = query.where(
            ActivityHistorySchema.is_reviewable == False  # noqa
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)

        return db_result.scalars().all()
