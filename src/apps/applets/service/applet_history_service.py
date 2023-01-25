from apps.activities.services import ActivityHistoryService
from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.domain import AppletHistory, AppletHistoryChange

__all__ = ["AppletHistoryService"]

from apps.shared.changes_generator import ChangeTextGenerator
from apps.shared.version import get_prev_version


class AppletHistoryService:
    def __init__(self, applet_id: int, version: str):
        self._applet_id = applet_id
        self._version = version
        self._id_version = f"{applet_id}_{version}"

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
