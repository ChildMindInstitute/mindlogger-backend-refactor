import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.activity_flows.db.schemas import ActivityFlowSchema
from infrastructure.database import BaseCRUD

__all__ = ["FlowsCRUD"]


class FlowsCRUD(BaseCRUD[ActivityFlowSchema]):
    schema_class = ActivityFlowSchema

    async def create_many(
        self,
        flow_schemas: list[ActivityFlowSchema],
    ) -> list[ActivityFlowSchema]:
        return await self._create_many(flow_schemas)

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        query = delete(ActivityFlowSchema).where(
            ActivityFlowSchema.applet_id == applet_id
        )
        await self._execute(query)

    async def get_by_applet_id(self, applet_id) -> list[ActivityFlowSchema]:
        query: Query = select(ActivityFlowSchema)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)
        query = query.order_by(ActivityFlowSchema.ordering.asc())
        result = await self._execute(query)
        return result.scalars().all()

    # Get by applet id and flow id
    async def get_by_applet_id_and_flow_id(
        self, applet_id: uuid.UUID, flow_id: uuid.UUID
    ) -> ActivityFlowSchema:
        query: Query = select(ActivityFlowSchema)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)
        query = query.where(ActivityFlowSchema.id == flow_id)

        result = await self._execute(query)
        return result.scalars().first()
