import uuid

from apps.applets.service import AppletService
from apps.migrate.services.activity_service import ActivityMigrationService
from apps.applets.crud import AppletsCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import (
    Role,
)
from apps.applets.domain.applet_create_update import (
    AppletCreate,
    AppletUpdate,
)
from apps.migrate.domain.applet_full import AppletMigratedFull
from apps.migrate.services.applet_history_service import (
    AppletMigrationHistoryService,
)
from apps.migrate.services.flow_service import FlowMigrationService
from apps.workspaces.service.user_applet_access import UserAppletAccessService

import datetime

__all__ = [
    "AppletMigrationService",
]


class AppletMigrationService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session
        self.decorated = AppletService(session, user_id)

    async def _create_applet_accesses(
        self, applet_id: uuid.UUID, manager_id: uuid.UUID | None
    ):
        # TODO: move to api level
        await UserAppletAccessService(
            self.session, self.user_id, applet_id
        ).add_role(self.user_id, Role.OWNER)

        await UserAppletAccessService(
            self.session, self.user_id, applet_id
        ).add_role(self.user_id, Role.RESPONDENT)

        if manager_id and manager_id != self.user_id:
            await UserAppletAccessService(
                self.session, self.user_id, applet_id
            ).add_role(manager_id, Role.MANAGER)

            await UserAppletAccessService(
                self.session, self.user_id, applet_id
            ).add_role(manager_id, Role.RESPONDENT)

    async def create(
        self, create_data: AppletCreate, manager_id: uuid.UUID | None = None
    ) -> AppletMigratedFull:
        applet = await self._create(create_data)

        await self.decorated._create_applet_accesses(applet.id, manager_id)

        applet.activities = await ActivityMigrationService(
            self.session, self.user_id
        ).create(applet, create_data.activities)
        activity_key_id_map = dict()
        for activity in applet.activities:
            activity_key_id_map[activity.key] = activity.id
        applet.activity_flows = await FlowMigrationService(
            self.session
        ).create(applet, create_data.activity_flows, activity_key_id_map)

        await AppletMigrationHistoryService(self.session).add_history(
            manager_id or self.user_id, applet
        )

        return applet

    async def _create(self, create_data: AppletCreate) -> AppletMigratedFull:
        applet_id = create_data.extra_fields["id"]
        await self.decorated._validate_applet_name(create_data.display_name)
        schema = await AppletsCRUD(self.session).save(
            AppletSchema(
                id=applet_id,
                display_name=create_data.display_name,
                description=create_data.description,
                about=create_data.about,
                image=create_data.image,
                watermark=create_data.watermark,
                theme_id=create_data.theme_id,
                version=create_data.extra_fields["version"],
                report_server_ip=create_data.report_server_ip,
                report_public_key=create_data.report_public_key,
                report_recipients=create_data.report_recipients,
                report_include_user_id=create_data.report_include_user_id,
                report_include_case_id=create_data.report_include_case_id,
                report_email_body=create_data.report_email_body,
                encryption=create_data.encryption.dict()
                if create_data.encryption
                else None,
                created_at=create_data.extra_fields['created'],
                updated_at=create_data.extra_fields["updated"],
                migrated_date=datetime.datetime.now(),
                migrated_updated=datetime.datetime.now(),
            )
        )
        return AppletMigratedFull.from_orm(schema)

    async def update(self, update_data: AppletCreate) -> AppletMigratedFull:
        applet_id = update_data.extra_fields["id"]
        old_applet = AppletMigratedFull.from_orm(
            await AppletsCRUD(self.session).get_by_id(applet_id)
        )
        next_version = update_data.extra_fields["version"]

        await FlowMigrationService(self.session).remove_applet_flows(
            old_applet
        )
        await ActivityMigrationService(
            self.session, self.user_id
        ).remove_applet_activities(applet_id)
        applet = await self._update(applet_id, update_data, next_version)

        applet.activities = await ActivityMigrationService(
            self.session, self.user_id
        ).update_create(applet, update_data.activities)
        activity_key_id_map = dict()
        for activity in applet.activities:
            activity_key_id_map[activity.key] = activity.id

        applet.activity_flows = await FlowMigrationService(
            self.session
        ).update_create(
            applet, update_data.activity_flows, activity_key_id_map
        )

        await AppletMigrationHistoryService(self.session).add_history(
            self.user_id, applet
        )

        return applet

    async def _update(
        self, applet_id: uuid.UUID, update_data: AppletCreate, version: str
    ) -> AppletMigratedFull:
        await self.decorated._validate_applet_name(
            update_data.display_name, applet_id
        )

        schema = await AppletsCRUD(self.session).update_by_id(
            applet_id,
            AppletSchema(
                display_name=update_data.display_name,
                description=update_data.description,
                encryption=update_data.encryption.dict()
                if update_data.encryption
                else None,
                about=update_data.about,
                image=update_data.image,
                watermark=update_data.watermark,
                theme_id=update_data.theme_id,
                version=version,
                report_server_ip=update_data.report_server_ip,
                report_public_key=update_data.report_public_key,
                report_recipients=update_data.report_recipients,
                report_include_user_id=update_data.report_include_user_id,
                report_include_case_id=update_data.report_include_case_id,
                report_email_body=update_data.report_email_body,
                created_at=update_data.extra_fields["created"],
                updated_at=update_data.extra_fields["updated"],
                migrated_date=datetime.datetime.now(),
                migrated_updated=datetime.datetime.now(),
            ),
        )
        return AppletMigratedFull.from_orm(schema)
