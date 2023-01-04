import uuid

import pydantic.types as types
import sqlalchemy as sa
from sqlalchemy import delete

import apps.activities.db.schemas as schemas
import apps.activities.domain as domain
from apps.activities.crud.activity_item import ActivityItemsCRUD
from infrastructure.database import BaseCRUD


class ActivitiesCRUD(BaseCRUD[schemas.ActivitySchema]):
    schema_class = schemas.ActivitySchema

    async def create_many(
        self,
        applet_id: int,
        activities_create: types.List[domain.ActivityCreate],
    ) -> list[domain.Activity]:
        activity_schemas = []
        activity_schema_map: dict[
            uuid.UUID, list[domain.ActivityItemCreate]
        ] = dict()
        for index, activity_create in enumerate(activities_create):
            activity_schema_map[activity_create.guid] = activity_create.items
            activity_schemas.append(
                schemas.ActivitySchema(
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

        instances: list[schemas.ActivitySchema] = await self._create_many(
            activity_schemas
        )
        activities: list[domain.Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()
        activity_id_map: dict[int, domain.Activity] = dict()

        for instance in instances:
            activity: domain.Activity = domain.Activity.from_orm(instance)
            activities.append(activity)
            activity_guid_id_map[activity.guid] = activity.id
            activity_id_map[activity.id] = activity

        items: list[
            domain.ActivityItem
        ] = await ActivityItemsCRUD().create_many(
            activity_guid_id_map, activity_schema_map
        )
        for item in items:
            activity_id_map[item.activity_id].items.append(item)

        return activities

    async def update_many(
        self,
        applet_id: int,
        activities_update: types.List[domain.ActivityUpdate],
    ) -> list[domain.Activity]:
        await self.clear_applet_activities(applet_id)

        activity_schemas = []
        activity_schema_map: dict[
            uuid.UUID, list[domain.ActivityItemUpdate]
        ] = dict()

        for index, activity_update in enumerate(activities_update):
            activity_schema_map[activity_update.guid] = activity_update.items
            if activity_update.id:
                activity_schemas.append(
                    self._update_to_schema(applet_id, index, activity_update)
                )

        instances: list[schemas.ActivitySchema] = await self._create_many(
            activity_schemas
        )
        activities: list[domain.Activity] = []
        activity_guid_id_map: dict[uuid.UUID, int] = dict()
        activity_id_map: dict[int, domain.Activity] = dict()

        for instance in instances:
            activity: domain.Activity = domain.Activity.from_orm(instance)
            activities.append(activity)
            activity_guid_id_map[activity.guid] = activity.id
            activity_id_map[activity.id] = activity

        items: list[
            domain.ActivityItem
        ] = await ActivityItemsCRUD().update_many(
            activity_guid_id_map, activity_schema_map
        )
        for item in items:
            activity_id_map[item.activity_id].items.append(item)

        return activities

    def _get_id_or_sequence(self, id_: int | None = None):
        return id_ or sa.Sequence(self.schema_class.sequence_name).next_value()

    async def clear_applet_activities(self, applet_id):
        await ActivityItemsCRUD().clear_applet_activity_items(
            sa.select(self.schema_class.id).where(
                self.schema_class.applet_id == applet_id
            )
        )
        query = delete(self.schema_class).where(
            self.schema_class.applet_id == applet_id
        )
        await self._execute(query)

    def _update_to_schema(
        self, applet_id: int, index: int, schema: domain.ActivityUpdate
    ):
        return self.schema_class(
            id=self._get_id_or_sequence(schema.id),
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
