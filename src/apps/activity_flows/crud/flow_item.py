import uuid

import pydantic.types as types
import sqlalchemy as sa
from sqlalchemy import delete

import apps.activity_flows.db.schemas as schemas
import apps.activity_flows.domain as domain
from infrastructure.database import BaseCRUD


class FlowItemsCRUD(BaseCRUD[schemas.ActivityFlowItemSchema]):
    schema_class = schemas.ActivityFlowItemSchema

    async def create(
        self,
        flow_id: int,
        item_create: domain.ActivityFlowItemCreate,
        ordering: int,
        activity_map: types.Dict[types.UUID4, int],
    ) -> domain.ActivityFlowItem:
        instance: schemas.ActivityFlowItemSchema = await self._create(
            schemas.ActivityFlowItemSchema(
                activity_flow_id=flow_id,
                activity_id=activity_map[item_create.activity_guid],
                ordering=ordering,
            )
        )
        return domain.ActivityFlowItem.from_orm(instance)

    async def create_many(
        self,
        flows_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[domain.ActivityFlowItemCreate]],
        activity_map: dict[uuid.UUID, int],
    ) -> list[domain.ActivityFlowItem]:
        items_schemas: list[schemas.ActivityFlowItemSchema] = []
        for flow_guid, items_create in items_map.items():
            flow_id: int = flows_map[flow_guid]
            for index, item_crete in enumerate(items_create):
                items_schemas.append(
                    schemas.ActivityFlowItemSchema(
                        activity_flow_id=flow_id,
                        activity_id=activity_map[item_crete.activity_guid],
                        ordering=index + 1,
                    )
                )

        instances = await self._create_many(items_schemas)
        items: list[domain.ActivityFlowItem] = []
        for instance in instances:
            items.append(domain.ActivityFlowItem.from_orm(instance))
        return items

    async def update_many(
        self,
        flows_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[domain.ActivityFlowItemUpdate]],
        activity_map: dict[uuid.UUID, int],
    ) -> list[domain.ActivityFlowItem]:
        items_schemas: list[schemas.ActivityFlowItemSchema] = []
        for flow_guid, items_create in items_map.items():
            flow_id: int = flows_map[flow_guid]
            for index, item_update in enumerate(items_create):
                items_schemas.append(
                    schemas.ActivityFlowItemSchema(
                        id=self._get_id_or_sequence(item_update.id),
                        activity_flow_id=flow_id,
                        activity_id=activity_map[item_update.activity_guid],
                        ordering=index + 1,
                    )
                )

        instances = await self._create_many(items_schemas)
        items: list[domain.ActivityFlowItem] = []
        for instance in instances:
            items.append(domain.ActivityFlowItem.from_orm(instance))
        return items

    def _get_id_or_sequence(self, id_: int | None = None):
        return id_ or sa.Sequence(self.schema_class.sequence_name).next_value()

    async def clear_applet_flow_items(self, flow_id_query):
        query = delete(self.schema_class).where(
            self.schema_class.activity_flow_id.in_(flow_id_query)
        )
        await self._execute(query)
