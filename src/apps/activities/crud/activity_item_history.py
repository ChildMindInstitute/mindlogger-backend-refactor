import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
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

    async def retrieve_by_applet_version(
        self, id_version: str
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == ActivityItemHistorySchema.activity_id,
        )
        query = query.filter(ActivityHistorySchema.applet_id == id_version)
        query = query.order_by(
            ActivityItemHistorySchema.order.asc(),
        )

        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_by_id_version(
        self, id_version: str
    ) -> ActivityItemHistorySchema:
        """
        This method might be redundant.
        It is leaved there because of changes from main branch.
        """

        query: Query = select(ActivityItemHistorySchema)
        query = query.where(ActivityItemHistorySchema.id_version == id_version)
        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def retrieve_by_id(
        self, _id: uuid.UUID
    ) -> ActivityItemHistorySchema:

        query: Query = select(ActivityItemHistorySchema)
        query = query.where(ActivityItemHistorySchema.id == _id)
        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def get_by_activity_id_version(
        self, activity_id: str
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(
            ActivityItemHistorySchema.activity_id == activity_id
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_id_versions(
        self, id_versions: list[str]
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(
            ActivityItemHistorySchema.id_version.in_(id_versions)
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_activity_id_versions(
        self, id_versions: list[str]
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(
            ActivityItemHistorySchema.activity_id.in_(id_versions)
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_applets_assessments(
        self, applet_id_version: str
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == ActivityItemHistorySchema.activity_id,
        )
        query = query.where(
            ActivityHistorySchema.applet_id == applet_id_version
        )
        query = query.where(
            ActivityHistorySchema.is_reviewable == True  # noqa: E712
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_activity_items(
        self, activity_id: uuid.UUID, versions: list[str] | None
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == ActivityItemHistorySchema.activity_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        if versions:
            query = query.join(
                AppletHistorySchema,
                AppletHistorySchema.id_version
                == ActivityHistorySchema.applet_id,
            )
            query = query.where(AppletHistorySchema.version.in_(versions))
        query = query.where(
            ActivityHistorySchema.is_reviewable == False  # noqa
        )
        query = query.order_by(ActivityItemHistorySchema.order.asc())
        db_result = await self._execute(query)

        return db_result.scalars().all()
