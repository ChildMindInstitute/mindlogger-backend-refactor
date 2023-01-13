from apps.activities.db.schemas import ActivityItemHistorySchema
from infrastructure.database import BaseCRUD


class ActivityItemsHistoryCRUD(BaseCRUD[ActivityItemHistorySchema]):
    schema_class = ActivityItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityItemHistorySchema],
    ):
        await self._create_many(items)
