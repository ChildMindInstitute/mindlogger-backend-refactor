from sqlalchemy import any_, select
from sqlalchemy.orm import Query

from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from infrastructure.database import BaseCRUD

__all__ = ["FlowsHistoryCRUD"]


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
        query = query.order_by(ActivityFlowHistoriesSchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_id_versions(
        self, id_versions: list[str]
    ) -> list[ActivityFlowHistoriesSchema]:
        if not id_versions:
            return []

        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(
            ActivityFlowHistoriesSchema.id_version == any_(id_versions)
        )
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_applet_id(
        self, applet_id: str
    ) -> list[ActivityFlowHistoriesSchema]:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.applet_id == applet_id)
        query = query.order_by(ActivityFlowHistoriesSchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()
