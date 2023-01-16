import uuid

import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy import delete

from apps.activity_flows.db.schemas import (
    ActivityFlowItemSchema,
    ActivityFlowSchema,
)
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import (
    creating_applet,
    fetching_applet,
    updating_applet,
)
from infrastructure.database import BaseCRUD


class FlowItemsCRUD(BaseCRUD[ActivityFlowItemSchema]):
    schema_class = ActivityFlowItemSchema

    async def create_many(
        self,
        flows_map: dict[uuid.UUID, int],
        items_map: dict[
            uuid.UUID, list[creating_applet.ActivityFlowItemCreate]
        ],
        activity_map: dict[uuid.UUID, fetching_applet.Activity],
    ) -> list[fetching_applet.ActivityFlowItem]:

        items_schemas: list[ActivityFlowItemSchema] = []
        for flow_guid, items_create in items_map.items():
            flow_id: int = flows_map[flow_guid]
            for index, item_crete in enumerate(items_create):
                activity = activity_map[item_crete.activity_guid]
                items_schemas.append(
                    ActivityFlowItemSchema(
                        activity_flow_id=flow_id,
                        activity_id=activity.id,
                        ordering=index + 1,
                    )
                )

        instances = await self._create_many(items_schemas)
        items: list[fetching_applet.ActivityFlowItem] = []
        for instance in instances:
            flow_item = fetching_applet.ActivityFlowItem.from_orm(instance)
            items.append(flow_item)
        return items

    async def update_many(
        self,
        flows_map: dict[uuid.UUID, int],
        items_map: dict[
            uuid.UUID, list[updating_applet.ActivityFlowItemUpdate]
        ],
        activity_map: dict[uuid.UUID, int],
    ) -> list[fetching_applet.ActivityFlowItem]:
        items_schemas: list[ActivityFlowItemSchema] = []
        for flow_guid, items_update in items_map.items():
            flow_id: int = flows_map[flow_guid]
            for index, item_update in enumerate(items_update):
                items_schemas.append(
                    ActivityFlowItemSchema(
                        id=item_update.id,
                        activity_flow_id=flow_id,
                        activity_id=activity_map[item_update.activity_guid],
                        ordering=index + 1,
                    )
                )

        instances = await self._create_many(items_schemas)
        items: list[fetching_applet.ActivityFlowItem] = []
        for instance in instances:
            items.append(fetching_applet.ActivityFlowItem.from_orm(instance))
        return items

    async def clear_applet_flow_items(self, flow_id_query):
        query = delete(self.schema_class).where(
            self.schema_class.activity_flow_id.in_(flow_id_query)
        )
        await self._execute(query)

    async def get_by_applet_id(
        self, applet_id
    ) -> list[ActivityFlowItemSchema]:
        query: sa.orm.Query = sa.select(ActivityFlowItemSchema)
        query = query.join(
            ActivityFlowSchema,
            (ActivityFlowSchema.id == ActivityFlowItemSchema.activity_flow_id),
        )
        query = query.join(
            AppletSchema,
            (AppletSchema.id == ActivityFlowSchema.applet_id),
        )
        query = query.where(AppletSchema.id == applet_id)
        query = query.order_by(
            ActivityFlowSchema.ordering.asc(),
            ActivityFlowItemSchema.ordering.asc(),
        )
        query = query.options(
            sa.orm.joinedload(ActivityFlowItemSchema.activity_flow)
        )
        result = await self._execute(query)
        results = result.scalars().all()
        return results
