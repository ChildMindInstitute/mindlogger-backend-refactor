from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.domain import AppletHistory, AppletHistoryChange
from apps.applets.domain.applets.history_detail import Applet
from apps.applets.helpers.version import get_prev_version
from apps.applets.service import ChangeTextGenerator

__all__ = ['AppletHistoryService']


class AppletHistoryService:
    def __init__(self, applet_id: int, version: str):
        self._applet_id = applet_id
        self._version = version
        self._id_version = f'{applet_id}_{version}'

    def get_detail(self) -> Applet:
        pass

    async def get_changes(self):
        prev_version = get_prev_version(self._version)
        old_id_version = f'{self._applet_id}_{prev_version}'

        changes = await self._get_applet_changes(old_id_version)


        return

    async def _get_applet_changes(
            self, old_id_version: str
    ) -> AppletHistoryChange:
        changes_generator = ChangeTextGenerator()
        changes = AppletHistoryChange()

        new_schema = await AppletHistoriesCRUD().fetch_by_id_version(
            self._id_version)
        old_schema = await AppletHistoriesCRUD().fetch_by_id_version(
            old_id_version)

        new_history: AppletHistory = AppletHistory.from_orm(new_schema)
        old_history: AppletHistory = AppletHistory.from_orm(old_schema)
        for field, old_value in old_history.dict():
            new_value = getattr(new_history, field)
            if not any([old_value, new_value]):
                continue
            if new_value == old_value:
                continue
            if changes_generator.is_considered_empty(new_value):
                setattr(changes, field, changes_generator.cleared_text(field))
            elif changes_generator.is_considered_empty(old_value):
                setattr(changes, field, changes_generator.filled_text(
                    field, new_value
                ))
            else:
                setattr(changes, field, changes_generator.changed_text(
                    old_value, new_value
                ))
        return changes
