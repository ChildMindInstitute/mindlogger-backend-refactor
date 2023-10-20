import uuid

from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.activity_flows.domain.flow_create import (
    FlowCreate,
    PreparedFlowItemCreate,
)
from apps.activity_flows.domain.flow_full import FlowFull
from apps.activity_flows.domain.flow_update import (
    FlowUpdate,
    PreparedFlowItemUpdate,
)
from apps.migrate.domain.applet_full import AppletMigratedFull
from apps.migrate.services.flow_item_service import FlowItemMigrationService
from apps.migrate.utilities import prepare_extra_fields_to_save


class FlowMigrationService:
    def __init__(self, session):
        self.session = session

    async def create(
        self,
        applet: AppletMigratedFull,
        flows_create: list[FlowCreate],
        activity_key_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> list[FlowFull]:
        schemas = list()
        prepared_flow_items = list()
        for index, flow_create in enumerate(flows_create):
            flow_id = flow_create.extra_fields["id"]
            schemas.append(
                ActivityFlowSchema(
                    id=flow_id,
                    applet_id=applet.id,
                    name=flow_create.name,
                    description=flow_create.description,
                    is_single_report=flow_create.is_single_report,
                    hide_badge=flow_create.hide_badge,
                    is_hidden=flow_create.is_hidden,
                    order=index + 1,
                    created_at=applet.created_at,
                    updated_at=applet.updated_at,
                    migrated_date=applet.migrated_date,
                    migrated_updated=applet.migrated_updated,
                    extra_fields=prepare_extra_fields_to_save(
                        flow_create.extra_fields
                    ),
                )
            )
            for flow_item_create in flow_create.items:
                prepared_flow_items.append(
                    PreparedFlowItemCreate(
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[
                            flow_item_create.activity_key
                        ],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemMigrationService(
            self.session, applet
        ).create(prepared_flow_items)
        flows = list()

        flow_id_map = dict()

        for flow_schema in flow_schemas:
            flow = FlowFull.from_orm(flow_schema)
            flows.append(flow)
            flow_id_map[flow.id] = flow

        for flow_item in flow_items:
            flow_id_map[flow_item.activity_flow_id].items.append(flow_item)

        return flows

    async def update_create(
        self,
        applet: AppletMigratedFull,
        flows_update: list[FlowCreate],
        activity_key_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> list[FlowFull]:
        schemas = list()
        prepared_flow_items = list()

        # Save new flow ids
        for index, flow_update in enumerate(flows_update):
            flow_id = flow_update.extra_fields["id"]

            schemas.append(
                ActivityFlowSchema(
                    id=flow_id,
                    applet_id=applet.id,
                    name=flow_update.name,
                    description=flow_update.description,
                    is_single_report=flow_update.is_single_report,
                    hide_badge=flow_update.hide_badge,
                    is_hidden=flow_update.is_hidden,
                    order=index + 1,
                    created_at=applet.created_at,
                    updated_at=applet.updated_at,
                    migrated_date=applet.migrated_date,
                    migrated_updated=applet.migrated_updated,
                )
            )
            for flow_item_update in flow_update.items:
                prepared_flow_items.append(
                    PreparedFlowItemUpdate(
                        id=uuid.uuid4(),
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[
                            flow_item_update.activity_key
                        ],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemMigrationService(
            self.session, applet
        ).create_update(prepared_flow_items)
        flows = list()

        flow_id_map = dict()

        for flow_schema in flow_schemas:
            flow = FlowFull.from_orm(flow_schema)
            flows.append(flow)
            flow_id_map[flow.id] = flow

        for flow_item in flow_items:
            flow_id_map[flow_item.activity_flow_id].items.append(flow_item)

        return flows

    async def remove_applet_flows(self, applet: AppletMigratedFull):
        await FlowItemMigrationService(
            self.session, applet
        ).remove_applet_flow_items(applet.id)
        await FlowsCRUD(self.session).delete_by_applet_id(applet.id)
