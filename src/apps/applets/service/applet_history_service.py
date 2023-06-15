import uuid

from apps.activities.services import ActivityHistoryService
from apps.activity_flows.service.flow_history import FlowHistoryService
from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain import AppletHistory, AppletHistoryChange

__all__ = ["AppletHistoryService"]

from apps.applets.domain.applet_full import AppletFull
from apps.applets.errors import InvalidVersionError, NotValidAppletHistory
from apps.shared.changes_generator import ChangeTextGenerator, ChangeGenerator
from apps.shared.version import get_prev_version


class AppletHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self._applet_id = applet_id
        self._version = version
        self._id_version = f"{applet_id}_{version}"
        self.session = session

    async def add_history(self, performer_id: uuid.UUID, applet: AppletFull):
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
            )
        )
        await ActivityHistoryService(
            self.session, applet.id, applet.version
        ).add(applet.activities)
        await FlowHistoryService(self.session, applet.id, applet.version).add(
            applet.activity_flows
        )

    async def get_changes(self) -> AppletHistoryChange:
        try:
            prev_version = get_prev_version(self._version)
        except ValueError:
            raise InvalidVersionError()
        old_id_version = f"{self._applet_id}_{prev_version}"

        changes = await self._get_applet_changes(old_id_version)
        changes.activities = await ActivityHistoryService(
            self.session, self._applet_id, self._version
        ).get_changes()
        return changes

    async def _get_applet_changes(
        self, old_id_version: str
    ) -> AppletHistoryChange:
        changes = AppletHistoryChange()

        new_schema = await AppletHistoriesCRUD(
            self.session
        ).fetch_by_id_version(self._id_version)
        old_schema = await AppletHistoriesCRUD(
            self.session
        ).fetch_by_id_version(old_id_version)

        new_history: AppletHistory = AppletHistory.from_orm(new_schema)
        old_history: AppletHistory = AppletHistory.from_orm(old_schema)

        if old_id_version == self._id_version:
            changes.display_name = (
                f"New applet {new_history.display_name} added"
            )

            return changes

        changes = ChangeGenerator().generate_applet_changes(
            new_history, old_history
        )

        return changes

    async def get(self) -> AppletHistory:
        schema = await AppletHistoriesCRUD(self.session).get_by_id_version(
            self._id_version
        )
        if not schema:
            raise NotValidAppletHistory()
        return AppletHistory.from_orm(schema)
