from sqlalchemy import select
from sqlalchemy.orm import Query, selectinload

from apps.activity_flows.db.schemas import (
    ActivityFlowHistoriesSchema,
    ActivityFlowItemHistorySchema,
)
from apps.applets.domain import detailing_history
from infrastructure.database import BaseCRUD


class FlowItemsHistoryCRUD(BaseCRUD[ActivityFlowItemHistorySchema]):
    schema_class = ActivityFlowItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityFlowItemHistorySchema],
    ):
        await self._create_many(items)

    async def list_by_applet_id_version(
        self,
        applet_id_version: str,
        activities_map: dict[str, detailing_history.Activity],
    ) -> list[detailing_history.ActivityFlow]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.join(
            ActivityFlowHistoriesSchema,
            ActivityFlowHistoriesSchema.id_version
            == ActivityFlowItemHistorySchema.activity_flow_id,
        )
        query = query.options(
            selectinload(ActivityFlowItemHistorySchema.activity_flow)
        )
        query = query.where(
            ActivityFlowHistoriesSchema.applet_id == applet_id_version
        )
        query = query.order_by(
            ActivityFlowHistoriesSchema.ordering.asc(),
            ActivityFlowItemHistorySchema.ordering.asc(),
        )
        result = await self._execute(query)
        results = result.scalars().all()
        flows: list[detailing_history.ActivityFlow] = []
        flow_map: dict[str, detailing_history.ActivityFlow] = dict()

        for item in results:  # type: ActivityFlowItemHistorySchema
            if item.activity_flow_id not in flow_map:
                flow = detailing_history.ActivityFlow.from_orm(
                    item.activity_flow
                )
                flows.append(flow)
                flow_map[item.activity_flow_id] = flow
            flow_item = detailing_history.ActivityFlowItem.from_orm(item)
            flow_item.activity = activities_map[flow_item.activity_id]
            flow_map[item.activity_flow_id].items.append(flow_item)
        return flows
