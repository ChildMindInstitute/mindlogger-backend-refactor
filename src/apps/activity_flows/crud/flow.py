import uuid

import sqlalchemy as sa
from sqlalchemy import delete

from apps.activity_flows.crud import FlowItemsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.activity_flows.domain import (
    ActivityFlow,
    ActivityFlowCreate,
    ActivityFlowItem,
    ActivityFlowItemCreate,
    ActivityFlowItemUpdate,
    ActivityFlowUpdate,
)
from infrastructure.database import BaseCRUD


class FlowsCRUD(BaseCRUD[ActivityFlowSchema]):
    schema_class = ActivityFlowSchema

    async def create_many(
        self,
        applet_id: int,
        flows_create: list[ActivityFlowCreate],
        activity_map: dict[uuid.UUID, int],
    ):
        flow_schemas: list[ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[ActivityFlowItemCreate]
        ] = dict()

        for index, flow_create in enumerate(flows_create):
            guid = uuid.uuid4()
            flow_schemas_map[guid] = flow_create.items
            flow_schemas.append(
                ActivityFlowSchema(
                    name=flow_create.name,
                    guid=guid,
                    description=flow_create.description,
                    applet_id=applet_id,
                    is_single_report=flow_create.is_single_report,
                    hide_badge=flow_create.hide_badge,
                    ordering=index + 1,
                )
            )
        instances: list[ActivityFlowSchema] = await self._create_many(
            flow_schemas
        )
        flows: list[ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()
        flow_id_map: dict[int, ActivityFlow] = dict()

        for instance in instances:
            flow: ActivityFlow = ActivityFlow.from_orm(instance)
            flows.append(flow)
            flow_guid_id_map[flow.guid] = flow.id
            flow_id_map[flow.id] = flow

        items: list[ActivityFlowItem] = await FlowItemsCRUD().create_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        for item in items:
            flow_id_map[item.activity_flow_id].items.append(item)
        return flows

    async def update_many(
        self,
        applet_id: int,
        flows_update: list[ActivityFlowUpdate],
        activity_map: dict[uuid.UUID, int],
    ):
        await self.clear_applet_flows(applet_id)

        flow_schemas: list[ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[ActivityFlowItemUpdate]
        ] = dict()

        for index, flow_update in enumerate(flows_update):
            guid = uuid.uuid4()
            flow_schemas_map[guid] = flow_update.items
            flow_schemas.append(
                ActivityFlowSchema(
                    id=flow_update.id or None,
                    name=flow_update.name,
                    guid=guid,
                    description=flow_update.description,
                    applet_id=applet_id,
                    is_single_report=flow_update.is_single_report,
                    hide_badge=flow_update.hide_badge,
                    ordering=index + 1,
                )
            )
        instances: list[ActivityFlowSchema] = await self._create_many(
            flow_schemas
        )
        flows: list[ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()
        flow_id_map: dict[int, ActivityFlow] = dict()

        for instance in instances:
            flow: ActivityFlow = ActivityFlow.from_orm(instance)
            flows.append(flow)
            flow_guid_id_map[flow.guid] = flow.id
            flow_id_map[flow.id] = flow

        items: list[ActivityFlowItem] = await FlowItemsCRUD().update_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        for item in items:
            flow_id_map[item.activity_flow_id].items.append(item)
        return flows

    async def clear_applet_flows(self, applet_id):
        await FlowItemsCRUD().clear_applet_flow_items(
            sa.select(self.schema_class.id).where(
                self.schema_class.applet_id == applet_id
            )
        )
        query = delete(self.schema_class).where(
            self.schema_class.applet_id == applet_id
        )
        await self._execute(query)

    async def get_by_applet_id(self, applet_id) -> list[ActivityFlow]:
        flows: list[ActivityFlow] = []
        flow_map = dict()
        items = await FlowItemsCRUD().get_by_applet_id(applet_id)

        for item in items:
            flow_id = item.activity_flow_id
            if flow_id not in flow_map:
                flow = ActivityFlow.from_orm(item.activity_flow)
                flow_map[flow_id] = flow
                flows.append(flow)
            flow_map[flow_id].items.append(ActivityFlowItem.from_orm(item))
        return flows
