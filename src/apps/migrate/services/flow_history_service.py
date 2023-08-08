import uuid

from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.activity_flows.domain.flow_full import FlowFull
from apps.migrate.domain.applet_full import AppletMigratedFull
from apps.migrate.services.flow_item_history_service import FlowItemHistoryMigrationService


class FlowHistoryMigrationService:
    def __init__(self, session, applet: AppletMigratedFull, version: str):
        self.applet = applet
        self.version = version
        self.applet_id_version = f"{applet.id}_{version}"
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
                    created_at=self.applet.created_at,
                    updated_at=self.applet.updated_at,
                    migrated_date=self.applet.migrated_date,
                    migrated_updated=self.applet.migrated_updated,
                )
            )

        await FlowsHistoryCRUD(self.session).create_many(schemas)
        await FlowItemHistoryMigrationService(
            self.session, self.applet, self.version
        ).add(flow_items)
