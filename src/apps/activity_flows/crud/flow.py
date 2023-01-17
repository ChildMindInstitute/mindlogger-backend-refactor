import uuid

import sqlalchemy as sa
from sqlalchemy import delete

from apps.activity_flows.crud.flow_item import FlowItemsCRUD
from apps.activity_flows.db.schemas import (
    ActivityFlowItemSchema,
    ActivityFlowSchema,
)
from apps.applets.domain import (
    creating_applet,
    detailing_applet,
    fetching_applet,
    updating_applet,
)
from infrastructure.database import BaseCRUD


class FlowsCRUD(BaseCRUD[ActivityFlowSchema]):
    schema_class = ActivityFlowSchema

    async def create_many(
        self,
        applet_id: int,
        flows_create: list[creating_applet.ActivityFlowCreate],
        activity_map: dict[uuid.UUID, fetching_applet.Activity],
    ) -> tuple[
        list[fetching_applet.ActivityFlow],
        list[fetching_applet.ActivityFlowItem],
    ]:
        flow_schemas: list[ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[creating_applet.ActivityFlowItemCreate]
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
        flows: list[fetching_applet.ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()

        for instance in instances:
            flows.append(fetching_applet.ActivityFlow.from_orm(instance))
            flow_guid_id_map[instance.guid] = instance.id

        flow_items = await FlowItemsCRUD().create_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        return flows, flow_items

    async def update_many(
        self,
        applet_id: int,
        flows_update: list[updating_applet.ActivityFlowUpdate],
        activity_map: dict[uuid.UUID, int],
    ) -> tuple[
        list[fetching_applet.ActivityFlow],
        list[fetching_applet.ActivityFlowItem],
    ]:
        flow_schemas: list[ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[updating_applet.ActivityFlowItemUpdate]
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
        flows: list[fetching_applet.ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()

        for instance in instances:
            flows.append(fetching_applet.ActivityFlow.from_orm(instance))
            flow_guid_id_map[instance.guid] = instance.id

        items = await FlowItemsCRUD().update_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        return flows, items

    async def clear_applet_flows(self, applet_id):
        await FlowItemsCRUD().clear_applet_flow_items(
            sa.select(ActivityFlowSchema.id).where(
                ActivityFlowSchema.applet_id == applet_id
            )
        )
        query = delete(ActivityFlowSchema).where(
            ActivityFlowSchema.applet_id == applet_id
        )
        await self._execute(query)

    async def get_by_applet_id(
        self, applet_id, activity_map: dict[int, detailing_applet.Activity]
    ) -> list[detailing_applet.ActivityFlow]:
        flows: list[detailing_applet.ActivityFlow] = []
        flow_map = dict()
        items = await FlowItemsCRUD().get_by_applet_id(applet_id)

        for item in items:  # type: ActivityFlowItemSchema
            flow_id = item.activity_flow_id
            if flow_id not in flow_map:
                flow = detailing_applet.ActivityFlow.from_orm(
                    item.activity_flow
                )
                flow_map[flow_id] = flow
                flows.append(flow)
            flow_item = detailing_applet.ActivityFlowItem.from_orm(item)
            flow_item.activity = activity_map[item.activity_id]
            flow_map[flow_id].items.append(flow_item)
        return flows
