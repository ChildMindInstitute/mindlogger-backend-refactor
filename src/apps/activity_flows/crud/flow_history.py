from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from infrastructure.database import BaseCRUD


class FlowsHistoryCRUD(BaseCRUD[ActivityFlowHistoriesSchema]):
    schema_class = ActivityFlowHistoriesSchema

    async def create_many(
        self,
        flows: list[ActivityFlowHistoriesSchema],
    ):
        await self._create_many(flows)
