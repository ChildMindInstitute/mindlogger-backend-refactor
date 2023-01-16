import uuid

import sqlalchemy as sa
import sqlalchemy.orm

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import (
    creating_applet,
    fetching_applet,
    updating_applet,
)
from infrastructure.database import BaseCRUD


class ActivityItemsCRUD(BaseCRUD[ActivityItemSchema]):
    schema_class = ActivityItemSchema

    async def create_many(
        self,
        activities_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[creating_applet.ActivityItemCreate]],
    ) -> list[fetching_applet.ActivityItem]:
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
        items: list[fetching_applet.ActivityItem] = []
        for instance in instances:
            items.append(fetching_applet.ActivityItem.from_orm(instance))
        return items

    async def update_many(
        self,
        activities_map: dict[uuid.UUID, int],
        items_map: dict[uuid.UUID, list[updating_applet.ActivityItemUpdate]],
    ) -> list[fetching_applet.ActivityItem]:
        items_schemas: list[ActivityItemSchema] = []
        for activity_guid, items_update in items_map.items():
            activity_id: int = activities_map[activity_guid]
            for index, item_update in enumerate(items_update):
                items_schemas.append(
                    self._update_to_schema(activity_id, index, item_update)
                )
        instances = await self._create_many(items_schemas)
        items: list[fetching_applet.ActivityItem] = []
        for instance in instances:
            items.append(fetching_applet.ActivityItem.from_orm(instance))
        return items

    async def clear_applet_activity_items(self, activity_id_query):
        query = sa.delete(self.schema_class).where(
            self.schema_class.activity_id.in_(activity_id_query)
        )
        await self._execute(query)

    def _update_to_schema(
        self,
        activity_id: int,
        index: int,
        update_item: updating_applet.ActivityItemUpdate,
    ):
        return ActivityItemSchema(
            activity_id=activity_id,
            question=update_item.question,
            response_type=update_item.response_type,
            answers=update_item.answers,
            color_palette=update_item.color_palette,
            timer=update_item.timer,
            has_token_value=update_item.has_token_value,
            is_skippable=update_item.is_skippable,
            has_alert=update_item.has_alert,
            has_score=update_item.has_score,
            is_random=update_item.is_random,
            has_text_response=update_item.has_text_response,
            ordering=index + 1,
            is_able_to_move_to_previous=(
                update_item.is_able_to_move_to_previous
            ),
        )

    async def get_by_applet_id(self, applet_id) -> list[ActivityItemSchema]:
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
