from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityHistorySchema
from infrastructure.database import BaseCRUD


class ActivitiesHistoryCRUD(BaseCRUD[ActivityHistorySchema]):
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
        query = query.order_by(ActivityHistorySchema.ordering.asc())
        result = await self._execute(query)
        return result.scalars().all()
