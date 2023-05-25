from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Query

from apps.activity_flows.db.schemas import (
    ActivityFlowHistoriesSchema,
    ActivityFlowItemHistorySchema,
)
from infrastructure.database import BaseCRUD

__all__ = ["FlowItemHistoriesCRUD"]


class FlowItemHistoriesCRUD(BaseCRUD[ActivityFlowItemHistorySchema]):
    schema_class = ActivityFlowItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityFlowItemHistorySchema],
    ):
        await self._create_many(items)

    async def retrieve_by_applet_version(
        self, id_version: str
    ) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.join(
            ActivityFlowHistoriesSchema,
            ActivityFlowHistoriesSchema.id_version
            == ActivityFlowItemHistorySchema.activity_flow_id,
        )
        query = query.where(
            ActivityFlowHistoriesSchema.applet_id == id_version
        )
        query = query.order_by(
            ActivityFlowItemHistorySchema.order.asc(),
        )
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_flow_id(
        self, flow_id: str
    ) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.where(
            ActivityFlowItemHistorySchema.activity_flow_id == flow_id
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_map(
        self, activity_flow_map: dict[str, str]
    ) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        filters = []
        for activity_id, flow_id in activity_flow_map.items():
            filters.append(
                and_(
                    ActivityFlowItemHistorySchema.activity_id == activity_id,
                    ActivityFlowItemHistorySchema.activity_flow_id == flow_id,
                )
            )

        query = query.where(or_(*filters))
        db_result = await self._execute(query)
        return db_result.scalars().all()
