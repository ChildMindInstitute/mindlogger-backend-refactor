import uuid

from sqlalchemy import delete, select

from apps.activity_flows.db.schemas import (
    ActivityFlowItemSchema,
    ActivityFlowSchema,
)
from apps.applets.db.schemas import AppletSchema
from infrastructure.database import BaseCRUD

__all__ = ["FlowItemsCRUD"]


class FlowItemsCRUD(BaseCRUD[ActivityFlowItemSchema]):
    schema_class = ActivityFlowItemSchema

    async def create_many(
        self, flow_items: list[ActivityFlowItemSchema]
    ) -> list[ActivityFlowItemSchema]:
        return await self._create_many(flow_items)

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        flow_id_query = select(ActivityFlowSchema.id).where(
            ActivityFlowSchema.applet_id == applet_id
        )
        query = delete(ActivityFlowItemSchema).where(
            ActivityFlowItemSchema.activity_flow_id.in_(flow_id_query)
        )
        await self._execute(query)

    async def get_by_applet_id(
        self, applet_id
    ) -> list[ActivityFlowItemSchema]:
        query = select(ActivityFlowItemSchema)
        query = query.join(
            ActivityFlowSchema,
            (ActivityFlowSchema.id == ActivityFlowItemSchema.activity_flow_id),
        )
        query = query.join(
            AppletSchema,
            (AppletSchema.id == ActivityFlowSchema.applet_id),
        )
        query = query.where(AppletSchema.id == applet_id)
        query = query.order_by(
            ActivityFlowItemSchema.order.asc(),
        )
        result = await self._execute(query)
        results = result.scalars().all()
        return results
