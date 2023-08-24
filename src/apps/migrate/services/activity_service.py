import uuid

from apps.activities.crud import ActivitiesCRUD
from apps.activities.db.schemas import ActivitySchema

from apps.activities.domain.activity_create import (
    ActivityCreate,
)

from apps.activities.domain.activity_full import ActivityFull
from apps.activities.domain.activity_update import (
    ActivityUpdate,
    PreparedActivityItemUpdate,
)
from apps.activities.services.activity_item import ActivityItemService
from apps.migrate.domain.activity_create import ActivityItemMigratedCreate
from apps.migrate.domain.applet_full import AppletMigratedFull


class ActivityMigrationService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def create(
        self,
        applet: AppletMigratedFull,
        activities_create: list[ActivityCreate],
    ) -> list[ActivityFull]:
        schemas = []
        activity_key_id_map: dict[uuid.UUID, uuid.UUID] = dict()
        activity_id_key_map: dict[uuid.UUID, uuid.UUID] = dict()
        prepared_activity_items = list()

        for index, activity_data in enumerate(activities_create):
            activity_id = activity_data.extra_fields["id"]
            activity_key_id_map[activity_data.key] = activity_id
            activity_id_key_map[activity_id] = activity_data.key

            schemas.append(
                ActivitySchema(
                    id=activity_id,
                    applet_id=applet.id,
                    name=activity_data.name,
                    description=activity_data.description,
                    splash_screen=activity_data.splash_screen,
                    image=activity_data.image,
                    show_all_at_once=activity_data.show_all_at_once,
                    is_skippable=activity_data.is_skippable,
                    is_reviewable=activity_data.is_reviewable,
                    response_is_editable=activity_data.response_is_editable,
                    is_hidden=activity_data.is_hidden,
                    scores_and_reports=activity_data.scores_and_reports.dict()
                    if activity_data.scores_and_reports
                    else None,
                    subscale_setting=activity_data.subscale_setting.dict()
                    if activity_data.subscale_setting
                    else None,
                    order=index + 1,
                    created_at=applet.created_at,
                    updated_at=applet.updated_at,
                    migrated_date=applet.migrated_date,
                    migrated_updated=applet.migrated_updated,
                )
            )

            for item in activity_data.items:
                prepared_activity_items.append(
                    ActivityItemMigratedCreate(
                        id=item.extra_fields["id"],
                        activity_id=activity_id,
                        question=item.question,
                        response_type=item.response_type,
                        response_values=item.response_values.dict()
                        if item.response_values
                        else None,
                        config=item.config.dict(),
                        name=item.name,
                        is_hidden=item.is_hidden,
                        conditional_logic=item.conditional_logic.dict()
                        if item.conditional_logic
                        else None,
                        allow_edit=item.allow_edit,
                        created_at=applet.created_at,
                        updated_at=applet.updated_at,
                        migrated_date=applet.migrated_date,
                        migrated_updated=applet.migrated_updated,
                    )
                )
        activity_schemas = await ActivitiesCRUD(self.session).create_many(
            schemas
        )
        activity_items = await ActivityItemService(self.session).create(
            prepared_activity_items
        )
        activities = list()

        activity_id_map: dict[uuid.UUID, ActivityFull] = dict()

        for activity_schema in activity_schemas:
            activity_schema.key = activity_id_key_map[activity_schema.id]
            activity = ActivityFull.from_orm(activity_schema)
            activities.append(activity)
            activity_id_map[activity.id] = activity

        for activity_item in activity_items:
            activity_id_map[activity_item.activity_id].items.append(
                activity_item
            )

        return activities

    async def update_create(
        self,
        applet: AppletMigratedFull,
        activities_create: list[ActivityUpdate],
    ) -> list[ActivityFull]:
        schemas = []
        activity_key_id_map: dict[uuid.UUID, uuid.UUID] = dict()
        activity_id_key_map: dict[uuid.UUID, uuid.UUID] = dict()
        prepared_activity_items = list()

        for index, activity_data in enumerate(activities_create):
            activity_id = activity_data.extra_fields["id"]
            activity_key_id_map[activity_data.key] = activity_id
            activity_id_key_map[activity_id] = activity_data.key

            schemas.append(
                ActivitySchema(
                    id=activity_id,
                    applet_id=applet.id,
                    name=activity_data.name,
                    description=activity_data.description,
                    splash_screen=activity_data.splash_screen,
                    image=activity_data.image,
                    show_all_at_once=activity_data.show_all_at_once,
                    is_skippable=activity_data.is_skippable,
                    is_reviewable=activity_data.is_reviewable,
                    response_is_editable=activity_data.response_is_editable,
                    is_hidden=activity_data.is_hidden,
                    scores_and_reports=activity_data.scores_and_reports.dict()
                    if activity_data.scores_and_reports
                    else None,
                    subscale_setting=activity_data.subscale_setting.dict()
                    if activity_data.subscale_setting
                    else None,
                    order=index + 1,
                    created_at=applet.created_at,
                    updated_at=applet.updated_at,
                    migrated_date=applet.migrated_date,
                    migrated_updated=applet.migrated_updated,
                )
            )

            for item in activity_data.items:
                prepared_activity_items.append(
                    ActivityItemMigratedCreate(
                        id=item.extra_fields["id"],
                        name=item.name,
                        activity_id=activity_id,
                        question=item.question,
                        response_type=item.response_type,
                        response_values=item.response_values.dict()
                        if item.response_values
                        else None,
                        config=item.config.dict(),
                        conditional_logic=item.conditional_logic.dict()
                        if item.conditional_logic
                        else None,
                        allow_edit=item.allow_edit,
                        created_at=applet.created_at,
                        updated_at=applet.updated_at,
                        migrated_date=applet.migrated_date,
                        migrated_updated=applet.migrated_updated,
                    )
                )
        activity_schemas = await ActivitiesCRUD(self.session).create_many(
            schemas
        )
        activity_items = await ActivityItemService(self.session).update_create(
            prepared_activity_items
        )
        activities = list()

        activity_id_map: dict[uuid.UUID, ActivityFull] = dict()

        for activity_schema in activity_schemas:
            activity_schema.key = activity_id_key_map[activity_schema.id]
            activity = ActivityFull.from_orm(activity_schema)
            activities.append(activity)
            activity_id_map[activity.id] = activity

        for activity_item in activity_items:
            activity_id_map[activity_item.activity_id].items.append(
                activity_item
            )

        return activities

    async def remove_applet_activities(self, applet_id: uuid.UUID):
        await ActivityItemService(self.session).remove_applet_activity_items(
            applet_id
        )
        await ActivitiesCRUD(self.session).delete_by_applet_id(applet_id)
