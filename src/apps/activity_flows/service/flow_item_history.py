import uuid

from apps.activity_flows.crud import FlowItemHistoriesCRUD
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema
from apps.activity_flows.domain.flow_full import (
    ActivityFlowItemFull,
    FlowItemHistoryFull,
)


class FlowItemHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version
        self.session = session

    async def add(self, flow_items: list[ActivityFlowItemFull]):
        schemas = []

        for item in flow_items:
            schemas.append(
                ActivityFlowItemHistorySchema(
                    order=item.order,
                    id_version=f"{item.id}_{self.version}",
                    id=item.id,
                    activity_flow_id=f"{item.activity_flow_id}_{self.version}",
                    activity_id=f"{item.activity_id}_{self.version}",
                )
            )

        await FlowItemHistoriesCRUD(self.session).create_many(schemas)

    async def get_activity_ids_by_flow_id(
        self, flow_id: uuid.UUID
    ) -> list[str]:
        flow_id_version = f"{flow_id}_{self.version}"
        schemas = await FlowItemHistoriesCRUD(self.session).get_by_flow_id(
            flow_id_version
        )

        return [schema.activity_id for schema in schemas]

    async def get_by_flow_ids(
        self, flow_ids: list[uuid.UUID]
    ) -> list[FlowItemHistoryFull]:
        schemas = await FlowItemHistoriesCRUD(self.session).get_by_flow_ids(
            [f"{pk}_{self.version}" for pk in flow_ids]
        )
        return [FlowItemHistoryFull.from_orm(schema) for schema in schemas]

    async def get_by_flow_id_versions(
        self, activity_id_versions: list[str]
    ) -> list[FlowItemHistoryFull]:
        return await FlowItemHistoriesCRUD(
            self.session
        ).get_by_flow_id_versions(activity_id_versions)
