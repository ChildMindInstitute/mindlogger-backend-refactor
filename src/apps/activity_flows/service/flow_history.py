import uuid

from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.activity_flows.domain.flow_full import FlowFull, FlowHistoryFull
from apps.activity_flows.service.flow_item_history import (
    FlowItemHistoryService,
)


class FlowHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version
        self.applet_id_version = f"{applet_id}_{version}"
        self.session = session

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
                    order=flow.order,
                )
            )

        await FlowsHistoryCRUD(self.session).create_many(schemas)
        await FlowItemHistoryService(
            self.session, self.applet_id, self.version
        ).add(flow_items)

    async def get_full(self) -> list[FlowHistoryFull]:
        schemas = await FlowsHistoryCRUD(self.session).get_by_applet_id(
            self.applet_id_version
        )
        flows = list()
        flow_map: dict[str, FlowHistoryFull] = dict()
        flow_ids = list()

        for schema in schemas:
            flow: FlowHistoryFull = FlowHistoryFull.from_orm(schema)
            flows.append(flow)
            flow_ids.append(flow.id)
            flow_map[flow.id_version] = flow

        items = await FlowItemHistoryService(
            self.session, self.applet_id, self.version
        ).get_by_flow_ids(flow_ids)

        for item in items:
            flow_map[item.activity_flow_id].items.append(item)

        return flows
