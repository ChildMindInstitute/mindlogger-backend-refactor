import uuid

import sqlalchemy as sa

from apps.activities.crud.activity_item import ActivityItemsCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.activities.domain import (
    Activity,
    ActivityCreate,
    ActivityItem,
    ActivityItemCreate,
    ActivityItemUpdate,
    ActivityUpdate,
)
from infrastructure.database import BaseCRUD


class ActivitiesCRUD(BaseCRUD[ActivitySchema]):
    schema_class = ActivitySchema

    async def create_many(
        self,
        applet_id: int,
        activities_create: list[ActivityCreate],
    ) -> list[Activity]:
        activity_schemas = []
        activity_schema_map: dict[uuid.UUID, list[ActivityItemCreate]] = dict()
        for index, activity_create in enumerate(activities_create):
            activity_schema_map[activity_create.guid] = activity_create.items
            activity_schemas.append(
                ActivitySchema(
                    applet_id=applet_id,
                    guid=activity_create.guid,
                    name=activity_create.name,
                    description=activity_create.description,
                    splash_screen=activity_create.splash_screen,
                    image=activity_create.image,
                    show_all_at_once=activity_create.show_all_at_once,
                    is_skippable=activity_create.is_skippable,
                    is_reviewable=activity_create.is_reviewable,
                    response_is_editable=activity_create.response_is_editable,
                    ordering=index + 1,
                )
            )

        instances: list[ActivitySchema] = await self._create_many(
            activity_schemas
        )
        activities: list[Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()
        activity_id_map: dict[int, Activity] = dict()

        for instance in instances:
            activity: Activity = Activity.from_orm(instance)
            activities.append(activity)
            activity_guid_id_map[activity.guid] = activity.id
            activity_id_map[activity.id] = activity

        items: list[ActivityItem] = await ActivityItemsCRUD().create_many(
            activity_guid_id_map, activity_schema_map
        )
        for item in items:
            activity_id_map[item.activity_id].items.append(item)

        return activities

    async def update_many(
        self,
        applet_id: int,
        activities_update: list[ActivityUpdate],
    ) -> list[Activity]:
        await self.clear_applet_activities(applet_id)

        activity_schemas = []
        activity_schema_map: dict[uuid.UUID, list[ActivityItemUpdate]] = dict()

        for index, activity_update in enumerate(activities_update):
            activity_schema_map[activity_update.guid] = activity_update.items
            activity_schemas.append(
                self._update_to_schema(applet_id, index, activity_update)
            )

        instances: list[ActivitySchema] = await self._create_many(
            activity_schemas
        )
        activities: list[Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()
        activity_id_map: dict[int, Activity] = dict()

        for instance in instances:
            activity: Activity = Activity.from_orm(instance)
            activities.append(activity)
            activity_guid_id_map[activity.guid] = activity.id
            activity_id_map[activity.id] = activity

        items: list[ActivityItem] = await ActivityItemsCRUD().update_many(
            activity_guid_id_map, activity_schema_map
        )
        for item in items:
            activity_id_map[item.activity_id].items.append(item)

        return activities

    async def clear_applet_activities(self, applet_id):
        await ActivityItemsCRUD().clear_applet_activity_items(
            sa.select(self.schema_class.id).where(
                self.schema_class.applet_id == applet_id
            )
        )
        query = sa.delete(self.schema_class).where(
            self.schema_class.applet_id == applet_id
        )
        await self._execute(query)

    def _update_to_schema(
        self, applet_id: int, index: int, schema: ActivityUpdate
    ):
        return self.schema_class(
            id=schema.id or None,
            applet_id=applet_id,
            guid=schema.guid,
            name=schema.name,
            description=schema.description,
            splash_screen=schema.splash_screen,
            image=schema.image,
            show_all_at_once=schema.show_all_at_once,
            is_skippable=schema.is_skippable,
            is_reviewable=schema.is_reviewable,
            response_is_editable=schema.response_is_editable,
            ordering=index + 1,
        )

    async def get_by_applet_id(self, id_: int) -> list[Activity]:
        activities = []
        activity_maps = dict()
        activity_items = await ActivityItemsCRUD().get_by_applet_id(id_)

        for activity_item in activity_items:
            activity_id = activity_item.activity.id
            if activity_id not in activity_maps:
                activity = Activity.from_orm(activity_item.activity)
                activity_maps[activity_id] = activity
                activities.append(activity)

            activity_maps[activity_id].items.append(
                ActivityItem.from_orm(activity_item)
            )

        return activities
