import uuid

from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.activity_flows.domain.flow_full import FlowFull
from apps.activity_flows.service.flow_item_history import (
    FlowItemHistoryService,
)


class FlowHistoryService:
    def __init__(self, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version
        self.applet_id_version = f"{applet_id}_{version}"

    async def add(self, flows: list[FlowFull]):
        flow_items = []
        schemas = []

        for flow in flows:
            flow_items += flow.items
            schemas.append(
                ActivityFlowHistoriesSchema(
                    id_version=f"{flow.id}_{self.version}",
                    id=flow.id,
                    applet_id=self.applet_id_version,
                    name=flow.name,
                    description=flow.description,
                    is_single_report=flow.is_single_report,
                    hide_badge=flow.hide_badge,
                    ordering=flow.ordering,
                )
            )

        await FlowsHistoryCRUD().create_many(schemas)
        await FlowItemHistoryService(self.applet_id, self.version).add(
            flow_items
        )
