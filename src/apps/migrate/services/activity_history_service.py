import uuid

from apps.activities.crud import ActivityHistoriesCRUD
from apps.activities.db.schemas import ActivityHistorySchema
from apps.activities.domain.activity_full import ActivityFull
from apps.migrate.domain.applet_full import AppletMigratedFull
from apps.migrate.services.activity_item_history_service import ActivityItemHistoryMigrationService

__all__ = ["ActivityHistoryMigrationService"]


class ActivityHistoryMigrationService:
    def __init__(self, session, applet: AppletMigratedFull, version: str):
        self._applet = applet
        self._version = version
        self._applet_id_version = f"{applet.id}_{version}"
        self.session = session

    async def add(self, activities: list[ActivityFull]):
        activity_items = []
        schemas = []

        for activity in activities:
            activity_items += activity.items
            schemas.append(
                ActivityHistorySchema(
                    id=activity.id,
                    id_version=f"{activity.id}_{self._version}",
                    applet_id=self._applet_id_version,
                    name=activity.name,
                    description=activity.description,
                    splash_screen=activity.splash_screen,
                    image=activity.image,
                    show_all_at_once=activity.show_all_at_once,
                    is_skippable=activity.is_skippable,
                    is_reviewable=activity.is_reviewable,
                    response_is_editable=activity.response_is_editable,
                    order=activity.order,
                    is_hidden=activity.is_hidden,
                    scores_and_reports=activity.scores_and_reports.dict()
                    if activity.scores_and_reports
                    else None,
                    subscale_setting=activity.subscale_setting.dict()
                    if activity.subscale_setting
                    else None,
                    created_at=self._applet.created_at,
                    updated_at=self._applet.updated_at,
                    migrated_date=self._applet.migrated_date,
                    migrated_updated=self._applet.migrated_updated,
                )
            )

        await ActivityHistoriesCRUD(self.session).create_many(schemas)
        await ActivityItemHistoryMigrationService(
            self.session, self._version, self._applet
        ).add(activity_items)
