import uuid
from collections import defaultdict

from apps.activity_flows.crud import FlowItemsCRUD
from apps.activity_flows.db.schemas import ActivityFlowItemSchema
from apps.activity_flows.domain.flow_create import PreparedFlowItemCreate
from apps.activity_flows.domain.flow_full import ActivityFlowItemFull
from apps.activity_flows.domain.flow_update import PreparedFlowItemUpdate


class FlowItemService:
    def __init__(self, session):
        self.session = session

    async def create(
        self, items: list[PreparedFlowItemCreate]
    ) -> list[ActivityFlowItemFull]:
        schemas = list()
        flow_id_ordering_map: dict[uuid.UUID, int] = defaultdict(int)

        for item in items:
            schemas.append(
                ActivityFlowItemSchema(
                    activity_flow_id=item.activity_flow_id,
                    activity_id=item.activity_id,
                    order=flow_id_ordering_map[item.activity_flow_id] + 1,
                )
            )
            flow_id_ordering_map[item.activity_flow_id] += 1
        item_schemas = await FlowItemsCRUD(self.session).create_many(schemas)

        return [
            ActivityFlowItemFull.from_orm(schema) for schema in item_schemas
        ]

    async def create_update(
        self, items: list[PreparedFlowItemUpdate]
    ) -> list[ActivityFlowItemFull]:
        schemas = list()
        flow_id_ordering_map: dict[uuid.UUID, int] = defaultdict(int)

        for item in items:
            schemas.append(
                ActivityFlowItemSchema(
                    id=item.id,
                    activity_flow_id=item.activity_flow_id,
                    activity_id=item.activity_id,
                    order=flow_id_ordering_map[item.activity_flow_id] + 1,
                )
            )
            flow_id_ordering_map[item.activity_flow_id] += 1
        item_schemas = await FlowItemsCRUD(self.session).create_many(schemas)

        return [
            ActivityFlowItemFull.from_orm(schema) for schema in item_schemas
        ]

    async def remove_applet_flow_items(self, applet_id: uuid.UUID):
        await FlowItemsCRUD(self.session).delete_by_applet_id(applet_id)

    async def get_by_flow_ids(
        self, flow_ids: list[uuid.UUID]
    ) -> list[ActivityFlowItemFull]:
        schemas = await FlowItemsCRUD(self.session).get_by_flow_ids(flow_ids)
        return [ActivityFlowItemFull.from_orm(schema) for schema in schemas]
