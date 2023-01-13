from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema
from infrastructure.database import BaseCRUD


class FlowItemsHistoryCRUD(BaseCRUD[ActivityFlowItemHistorySchema]):
    schema_class = ActivityFlowItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityFlowItemHistorySchema],
    ):
        await self._create_many(items)
