from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from infrastructure.database import BaseCRUD


class FlowsHistoryCRUD(BaseCRUD[ActivityFlowHistoriesSchema]):
    schema_class = ActivityFlowHistoriesSchema

    async def create_many(
        self,
        flows: list[ActivityFlowHistoriesSchema],
    ):
        await self._create_many(flows)

    async def retrieve_by_applet_version(
        self, id_version: str
    ) -> list[ActivityFlowHistoriesSchema]:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(
            ActivityFlowHistoriesSchema.applet_id == id_version
        )
        query = query.order_by(ActivityFlowHistoriesSchema.ordering.asc())
        result = await self._execute(query)
        return result.scalars().all()
