import uuid

from apps.activity_flows.crud import FlowItemHistoriesCRUD
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema
from apps.activity_flows.domain.flow_full import ActivityFlowItemFull


class FlowItemHistoryService:
    def __init__(self, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version

    async def add(self, flow_items: list[ActivityFlowItemFull]):
        schemas = []

        for item in flow_items:
            schemas.append(
                ActivityFlowItemHistorySchema(
                    ordering=item.ordering,
                    id_version=f"{item.id}_{self.version}",
                    id=item.id,
                    activity_flow_id=f"{item.activity_flow_id}_{self.version}",
                    activity_id=f"{item.activity_id}_{self.version}",
                )
            )

        await FlowItemHistoriesCRUD().create_many(schemas)

    async def get_activity_ids_by_flow_id(
        self, flow_id: uuid.UUID
    ) -> list[str]:
        flow_id_version = f"{flow_id}_{self.version}"
        schemas = await FlowItemHistoriesCRUD().get_by_flow_id(flow_id_version)

        return [schema.activity_id for schema in schemas]
