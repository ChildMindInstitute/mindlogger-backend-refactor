from apps.activities.db.schemas import ActivityHistorySchema
from infrastructure.database import BaseCRUD


class ActivitiesHistoryCRUD(BaseCRUD[ActivityHistorySchema]):
    schema_class = ActivityHistorySchema

    async def create_many(
        self,
        activities: list[ActivityHistorySchema],
    ):
        await self._create_many(activities)
