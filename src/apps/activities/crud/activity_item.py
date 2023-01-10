import uuid

import sqlalchemy as sa
import sqlalchemy.orm

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema
from apps.activities.domain import (
    ActivityItem,
    ActivityItemCreate,
    ActivityItemUpdate,
)
from apps.applets.db.schemas import AppletSchema
from infrastructure.database import BaseCRUD


class ActivityItemsCRUD(BaseCRUD[ActivityItemSchema]):
    schema_class = ActivityItemSchema

    async def create_many(
        self,
        activities_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[ActivityItemCreate]],
    ) -> list[ActivityItem]:
        items_schemas: list[ActivityItemSchema] = []
        for activity_guid, items_create in items_map.items():
            activity_id: int = activities_map[activity_guid]
            for index, item_create in enumerate(items_create):
                items_schemas.append(
                    ActivityItemSchema(
                        activity_id=activity_id,
                        question=item_create.question,
                        response_type=item_create.response_type,
                        answers=item_create.answers,
                        color_palette=item_create.color_palette,
                        timer=item_create.timer,
                        has_token_value=item_create.has_token_value,
                        is_skippable=item_create.is_skippable,
                        has_alert=item_create.has_alert,
                        has_score=item_create.has_score,
                        is_random=item_create.is_random,
                        is_able_to_move_to_previous=(
                            item_create.is_able_to_move_to_previous
                        ),
                        has_text_response=item_create.has_text_response,
                        ordering=index + 1,
                    )
                )
        instances = await self._create_many(items_schemas)
        items: list[ActivityItem] = []
        for instance in instances:
            items.append(ActivityItem.from_orm(instance))
        return items

    async def update_many(
        self,
        activities_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[ActivityItemUpdate]],
    ) -> list[ActivityItem]:
        items_schemas: list[ActivityItemSchema] = []
        for activity_guid, items_update in items_map.items():
            activity_id: int = activities_map[activity_guid]
            for index, item_update in enumerate(items_update):
                items_schemas.append(
                    self._update_to_schema(activity_id, index, item_update)
                )
        instances = await self._create_many(items_schemas)
        items: list[ActivityItem] = []
        for instance in instances:
            items.append(ActivityItem.from_orm(instance))
        return items

    async def clear_applet_activity_items(self, activity_id_query):
        query = sa.delete(self.schema_class).where(
            self.schema_class.activity_id.in_(activity_id_query)
        )
        await self._execute(query)

    def _update_to_schema(
        self, activity_id: int, index: int, schema: ActivityItemUpdate
    ):
        return ActivityItemSchema(
            id=schema.id or None,
            activity_id=activity_id,
            question=schema.question,
            response_type=schema.response_type,
            answers=schema.answers,
            color_palette=schema.color_palette,
            timer=schema.timer,
            has_token_value=schema.has_token_value,
            is_skippable=schema.is_skippable,
            has_alert=schema.has_alert,
            has_score=schema.has_score,
            is_random=schema.is_random,
            is_able_to_move_to_previous=schema.is_able_to_move_to_previous,
            has_text_response=schema.has_text_response,
            ordering=index + 1,
        )

    async def get_by_applet_id(self, applet_id):
        query = sa.select(ActivityItemSchema)
        query = query.join(
            ActivitySchema,
            ActivitySchema.id == ActivityItemSchema.activity_id,
        )
        query = query.join(
            AppletSchema,
            AppletSchema.id == ActivitySchema.applet_id,
        )
        query = query.where(AppletSchema.id == applet_id)
        query = query.order_by(
            ActivitySchema.ordering.asc(),
            ActivityItemSchema.ordering.asc(),
        )
        query = query.options(
            sa.orm.joinedload(ActivityItemSchema.activity),
        )
        result = await self._execute(query)
        results = result.scalars().all()
        return results
