import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Query

from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.activity_flows.domain.flow import Flow
from infrastructure.database import BaseCRUD

__all__ = ["FlowsCRUD"]


class FlowsCRUD(BaseCRUD[ActivityFlowSchema]):
    schema_class = ActivityFlowSchema

    async def get_by_id(self, id_: uuid.UUID) -> Flow | None:
        flow = await self._get("id", id_)
        if flow:
            return Flow.from_orm(flow)
        return None

    async def update_by_id(self, id_, **values):
        query = update(self.schema_class)
        query = query.where(self.schema_class.id == id_)
        query = query.values(**values)
        query = query.returning(self.schema_class)
        await self._execute(query)

    async def create_many(
        self,
        flow_schemas: list[ActivityFlowSchema],
    ) -> list[ActivityFlowSchema]:
        return await self._create_many(flow_schemas)

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        query = delete(ActivityFlowSchema).where(ActivityFlowSchema.applet_id == applet_id)
        await self._execute(query)

    async def get_by_applet_id(self, applet_id) -> list[ActivityFlowSchema]:
        query: Query = select(ActivityFlowSchema)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)
        query = query.order_by(ActivityFlowSchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    # Get by applet id and flow id
    async def get_by_applet_id_and_flow_id(self, applet_id: uuid.UUID, flow_id: uuid.UUID) -> ActivityFlowSchema:
        query: Query = select(ActivityFlowSchema)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)
        query = query.where(ActivityFlowSchema.id == flow_id)

        result = await self._execute(query)
        return result.scalars().first()

    async def get_by_applet_id_and_flows_ids(self, applet_id, flows_ids: list[uuid.UUID]) -> list[ActivityFlowSchema]:
        query: Query = select(ActivityFlowSchema)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)
        query = query.where(ActivityFlowSchema.id.in_(flows_ids))
        query = query.order_by(ActivityFlowSchema.order.asc())

        result = await self._execute(query)
        return result.scalars().all()

    async def get_ids_by_applet_id(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        query: Query = select(ActivityFlowSchema.id)
        query = query.where(ActivityFlowSchema.applet_id == applet_id)

        result = await self._execute(query)
        return result.scalars().all()
