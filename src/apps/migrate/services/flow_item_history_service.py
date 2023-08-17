import uuid

from apps.activity_flows.crud import FlowItemHistoriesCRUD
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema
from apps.activity_flows.domain.flow_full import (
    ActivityFlowItemFull,
)
from apps.migrate.domain.applet_full import AppletMigratedFull


class FlowItemHistoryMigrationService:
    def __init__(self, session, applet: AppletMigratedFull, version: str):
        self.applet = applet
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
                    created_at=self.applet.created_at,
                    updated_at=self.applet.updated_at,
                    migrated_date=self.applet.migrated_date,
                    migrated_updated=self.applet.migrated_updated,
                )
            )

        await FlowItemHistoriesCRUD(self.session).create_many(schemas)
