from apps.activities.crud import ActivityItemHistoriesCRUD
from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.migrate.domain.activity_full import (
    ActivityItemMigratedFull,
)
from apps.migrate.domain.applet_full import AppletMigratedFull
from apps.migrate.utilities import prepare_extra_fields_to_save


class ActivityItemHistoryMigrationService:
    def __init__(self, session, version: str, applet: AppletMigratedFull):
        self.version = version
        self.session = session
        self._applet = applet

    async def add(self, activity_items: list[ActivityItemMigratedFull]):
        schemas = []

        for item in activity_items:
            schemas.append(
                ActivityItemHistorySchema(
                    id=item.id,
                    id_version=f"{item.id}_{self.version}",
                    activity_id=f"{item.activity_id}_{self.version}",
                    question=item.question,
                    response_type=item.response_type,
                    response_values=item.response_values.dict()
                    if item.response_values
                    else None,
                    config=item.config.dict(),
                    order=item.order,
                    name=item.name,
                    conditional_logic=item.conditional_logic.dict()
                    if item.conditional_logic
                    else None,
                    allow_edit=item.allow_edit,
                    created_at=self._applet.created_at,
                    updated_at=self._applet.updated_at,
                    migrated_date=self._applet.migrated_date,
                    migrated_updated=self._applet.migrated_updated,
                    extra_fields={},
                )
            )
        await ActivityItemHistoriesCRUD(self.session).create_many(schemas)
