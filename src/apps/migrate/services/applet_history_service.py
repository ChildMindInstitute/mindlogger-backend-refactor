import uuid

from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.db.schemas import AppletHistorySchema
from apps.migrate.domain.applet_full import AppletMigratedFull

__all__ = ["AppletMigrationHistoryService"]

from apps.migrate.services.activity_history_service import (
    ActivityHistoryMigrationService,
)
from apps.migrate.services.flow_history_service import (
    FlowHistoryMigrationService,
)
from apps.migrate.utilities import prepare_extra_fields_to_save


class AppletMigrationHistoryService:
    def __init__(self, session):
        self.session = session

    async def add_history(
        self,
        performer_id: uuid.UUID,
        applet: AppletMigratedFull,
        initial_applet: bool = False,
    ):
        await AppletHistoriesCRUD(self.session).save(
            AppletHistorySchema(
                id=applet.id,
                user_id=performer_id,
                id_version=f"{applet.id}_{applet.version}",
                display_name=applet.display_name,
                description=applet.description,
                about=applet.about,
                image=applet.image,
                watermark=applet.watermark,
                theme_id=applet.theme_id,
                version=applet.version,
                report_server_ip=applet.report_server_ip,
                report_public_key=applet.report_public_key,
                report_recipients=applet.report_recipients,
                report_include_user_id=applet.report_include_user_id,
                report_include_case_id=applet.report_include_case_id,
                report_email_body=applet.report_email_body,
                created_at=applet.created_at
                if initial_applet
                else applet.updated_at,
                updated_at=applet.created_at
                if initial_applet
                else applet.updated_at,
                migrated_date=applet.migrated_date,
                migrated_updated=applet.migrated_updated,
                extra_fields=prepare_extra_fields_to_save(applet.extra_fields),
            )
        )
        await ActivityHistoryMigrationService(
            self.session, applet, applet.version
        ).add(applet.activities)
        await FlowHistoryMigrationService(
            self.session, applet, applet.version
        ).add(applet.activity_flows)
