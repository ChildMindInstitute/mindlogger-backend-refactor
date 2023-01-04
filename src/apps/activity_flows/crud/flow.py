import uuid

import sqlalchemy as sa
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

import apps.activity_flows.db.schemas as schemas
import apps.activity_flows.domain as domain
from apps.activity_flows.crud.flow_item import FlowItemsCRUD
from infrastructure.database import BaseCRUD


class FlowsCRUD(BaseCRUD[schemas.ActivityFlowSchema]):
    schema_class = schemas.ActivityFlowSchema

    async def create(
        self,
        applet_id: int,
        flow_create: domain.ActivityFlowCreate,
        ordering: int,
        activity_map: dict[uuid.UUID, int],
    ) -> domain.ActivityFlow:
        try:
            instance: schemas.ActivityFlowSchema = await self._create(
                schemas.ActivityFlowSchema(
                    name=flow_create.name,
                    description=flow_create.description,
                    applet_id=applet_id,
                    is_single_report=flow_create.is_single_report,
                    hide_badge=flow_create.hide_badge,
                    ordering=ordering,
                )
            )
        except IntegrityError:
            raise

        flow: domain.ActivityFlow = domain.ActivityFlow.from_orm(instance)

        for index, item in enumerate(flow_create.items):
            flow.items.append(
                await FlowItemsCRUD().create(
                    flow.id, item, index + 1, activity_map
                )
            )
        return flow

    async def create_many(
        self,
        applet_id: int,
        flows_create: list[domain.ActivityFlowCreate],
        activity_map: dict[uuid.UUID, int],
    ):
        flow_schemas: list[schemas.ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[domain.ActivityFlowItemCreate]
        ] = dict()

        for index, flow_create in enumerate(flows_create):
            guid = uuid.uuid4()
            flow_schemas_map[guid] = flow_create.items
            flow_schemas.append(
                schemas.ActivityFlowSchema(
                    name=flow_create.name,
                    guid=guid,
                    description=flow_create.description,
                    applet_id=applet_id,
                    is_single_report=flow_create.is_single_report,
                    hide_badge=flow_create.hide_badge,
                    ordering=index + 1,
                )
            )
        instances: list[schemas.ActivityFlowSchema] = await self._create_many(
            flow_schemas
        )
        flows: list[domain.ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()
        flow_id_map: dict[int, domain.ActivityFlow] = dict()

        for instance in instances:
            flow: domain.ActivityFlow = domain.ActivityFlow.from_orm(instance)
            flows.append(flow)
            flow_guid_id_map[flow.guid] = flow.id
            flow_id_map[flow.id] = flow

        items: list[
            domain.ActivityFlowItem
        ] = await FlowItemsCRUD().create_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        for item in items:
            flow_id_map[item.activity_flow_id].items.append(item)
        return flows

    async def update_many(
        self,
        applet_id: int,
        flows_update: list[domain.ActivityFlowUpdate],
        activity_map: dict[uuid.UUID, int],
    ):
        await self.clear_applet_flows(applet_id)

        flow_schemas: list[schemas.ActivityFlowSchema] = []
        flow_schemas_map: dict[
            uuid.UUID, list[domain.ActivityFlowItemUpdate]
        ] = dict()

        for index, flow_update in enumerate(flows_update):
            guid = uuid.uuid4()
            flow_schemas_map[guid] = flow_update.items
            flow_schemas.append(
                schemas.ActivityFlowSchema(
                    id=self._get_id_or_sequence(flow_update.id),
                    name=flow_update.name,
                    guid=guid,
                    description=flow_update.description,
                    applet_id=applet_id,
                    is_single_report=flow_update.is_single_report,
                    hide_badge=flow_update.hide_badge,
                    ordering=index + 1,
                )
            )
        instances: list[schemas.ActivityFlowSchema] = await self._create_many(
            flow_schemas
        )
        flows: list[domain.ActivityFlow] = []
        flow_guid_id_map: dict[uuid.UUID, int] = dict()
        flow_id_map: dict[int, domain.ActivityFlow] = dict()

        for instance in instances:
            flow: domain.ActivityFlow = domain.ActivityFlow.from_orm(instance)
            flows.append(flow)
            flow_guid_id_map[flow.guid] = flow.id
            flow_id_map[flow.id] = flow

        items: list[
            domain.ActivityFlowItem
        ] = await FlowItemsCRUD().update_many(
            flow_guid_id_map, flow_schemas_map, activity_map
        )

        for item in items:
            flow_id_map[item.activity_flow_id].items.append(item)
        return flows

    def _get_id_or_sequence(self, id_: int | None = None):
        return id_ or sa.Sequence(self.schema_class.sequence_name).next_value()

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
