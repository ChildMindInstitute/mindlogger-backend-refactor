from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
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

    async def get_by_activity_id_version(
        self, activity_id: str
    ) -> list[ActivityItemHistorySchema]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.where(
            ActivityItemHistorySchema.activity_id == activity_id
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()
