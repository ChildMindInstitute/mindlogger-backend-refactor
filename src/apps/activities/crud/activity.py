import uuid

import sqlalchemy as sa

from apps.activities.crud.activity_item import ActivityItemsCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.applets.domain import (
    creating_applet,
    detailing_applet,
    fetching_applet,
    updating_applet,
)
from infrastructure.database import BaseCRUD


class ActivitiesCRUD(BaseCRUD[ActivitySchema]):
    schema_class = ActivitySchema

    async def create_many(
        self,
        applet_id: int,
        activities_create: list[creating_applet.ActivityCreate],
    ) -> tuple[
        list[fetching_applet.Activity], list[fetching_applet.ActivityItem]
    ]:
        activity_schemas = []
        activity_schema_map: dict[
            uuid.UUID, list[creating_applet.ActivityItemCreate]
        ] = dict()
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

        instances = await self._create_many(activity_schemas)
        activities: list[fetching_applet.Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()

        for instance in instances:
            activities.append(fetching_applet.Activity.from_orm(instance))
            activity_guid_id_map[instance.guid] = instance.id

        items = await ActivityItemsCRUD().create_many(
            activity_guid_id_map, activity_schema_map
        )

        return activities, items

    async def update_many(
        self,
        applet_id: int,
        activities_update: list[updating_applet.ActivityUpdate],
    ) -> tuple[
        list[fetching_applet.Activity], list[fetching_applet.ActivityItem]
    ]:
        activity_schemas = []
        activity_schema_map: dict[
            uuid.UUID, list[updating_applet.ActivityItemUpdate]
        ] = dict()

        for index, activity_update in enumerate(activities_update):
            activity_schema_map[activity_update.guid] = activity_update.items
            activity_schemas.append(
                self._update_to_schema(applet_id, index, activity_update)
            )

        instances: list[ActivitySchema] = await self._create_many(
            activity_schemas
        )
        activities: list[fetching_applet.Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()

        for instance in instances:
            activities.append(fetching_applet.Activity.from_orm(instance))
            activity_guid_id_map[instance.guid] = instance.id

        items = await ActivityItemsCRUD().update_many(
            activity_guid_id_map, activity_schema_map
        )

        return activities, items

    async def clear_applet_activities(self, applet_id):
        await ActivityItemsCRUD().clear_applet_activity_items(
            sa.select(ActivitySchema.id).where(
                ActivitySchema.applet_id == applet_id
            )
        )
        query = sa.delete(ActivitySchema).where(
            ActivitySchema.applet_id == applet_id
        )
        await self._execute(query)

    def _update_to_schema(
        self,
        applet_id: int,
        index: int,
        activity_update: updating_applet.ActivityUpdate,
    ):
        return ActivitySchema(
            id=activity_update.id or None,
            applet_id=applet_id,
            guid=activity_update.guid,
            name=activity_update.name,
            description=activity_update.description,
            splash_screen=activity_update.splash_screen,
            image=activity_update.image,
            show_all_at_once=activity_update.show_all_at_once,
            is_skippable=activity_update.is_skippable,
            is_reviewable=activity_update.is_reviewable,
            response_is_editable=activity_update.response_is_editable,
            ordering=index + 1,
        )

    async def get_by_applet_id(
        self, id_: int
    ) -> tuple[
        list[detailing_applet.Activity], dict[int, detailing_applet.Activity]
    ]:
        activities = []
        activity_maps = dict()
        activity_items = await ActivityItemsCRUD().get_by_applet_id(id_)

        for activity_item in activity_items:
            activity_id = activity_item.activity.id
            if activity_id not in activity_maps:
                activity = detailing_applet.Activity.from_orm(
                    activity_item.activity
                )
                activity_maps[activity_id] = activity
                activities.append(activity)

            activity_maps[activity_id].items.append(
                detailing_applet.ActivityItem.from_orm(activity_item)
            )

        return activities, activity_maps
