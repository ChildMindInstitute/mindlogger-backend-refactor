import uuid

from apps.activities.services import ActivityHistoryService
from apps.activity_flows.service.flow_history import FlowHistoryService
from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain import AppletHistory, AppletHistoryChange

__all__ = ["AppletHistoryService"]

from apps.applets.domain.applet_full import AppletFull
from apps.applets.errors import NotValidAppletHistory
from apps.shared.changes_generator import ChangeTextGenerator
from apps.shared.version import get_prev_version


class AppletHistoryService:
    def __init__(self, applet_id: uuid.UUID, version: str):
        self._applet_id = applet_id
        self._version = version
        self._id_version = f"{applet_id}_{version}"

    async def add_history(self, performer_id: uuid.UUID, applet: AppletFull):
        await AppletHistoriesCRUD().save(
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
        await ActivityHistoryService(applet.id, applet.version).add(
            applet.activities
        )
        await FlowHistoryService(applet.id, applet.version).add(
            applet.activity_flows
        )

    async def get_changes(self) -> AppletHistoryChange:
        prev_version = get_prev_version(self._version)
        old_id_version = f"{self._applet_id}_{prev_version}"

        changes = await self._get_applet_changes(old_id_version)
        changes.activities = await ActivityHistoryService(
            self._applet_id, self._version
        ).get_changes()
        return changes

    async def _get_applet_changes(
        self, old_id_version: str
    ) -> AppletHistoryChange:
        changes_generator = ChangeTextGenerator()
        changes = AppletHistoryChange()

        new_schema = await AppletHistoriesCRUD().fetch_by_id_version(
            self._id_version
        )
        old_schema = await AppletHistoriesCRUD().fetch_by_id_version(
            old_id_version
        )

        new_history: AppletHistory = AppletHistory.from_orm(new_schema)
        old_history: AppletHistory = AppletHistory.from_orm(old_schema)
        for field, old_value in old_history.dict().items():
            new_value = getattr(new_history, field)
            if not any([old_value, new_value]):
                continue
            if new_value == old_value:
                continue
            if changes_generator.is_considered_empty(new_value):
                setattr(changes, field, changes_generator.cleared_text(field))
            elif changes_generator.is_considered_empty(old_value):
                setattr(
                    changes,
                    field,
                    changes_generator.filled_text(field, new_value),
                )
            else:
                setattr(
                    changes,
                    field,
                    changes_generator.changed_text(old_value, new_value),
                )
        return changes

    async def get(self) -> AppletHistory:
        schema = await AppletHistoriesCRUD().get_by_id(self._id_version)
        if not schema:
            raise NotValidAppletHistory()
        return AppletHistory.from_orm(schema)
