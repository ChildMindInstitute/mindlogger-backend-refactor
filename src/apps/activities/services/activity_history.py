from apps.activities.crud import ActivityHistoriesCRUD
from apps.applets.helpers.version import get_prev_version


class ActivityHistoryService:

    def __init__(self, applet_id: str, version: str):
        self._applet_id = applet_id
        self._version = version
        self._applet_id_version = f'{applet_id}_{version}'

    async def get_changes(self):
        prev_version = get_prev_version(self._version)
        old_id_version = f'{self._applet_id}_{prev_version}'


    async def _get_activity_changes(self, old_applet_id_version:str):
        activities = await ActivityHistoriesCRUD().retrieve_by_applet_versions_ordered_by_id([self._applet_id_version, old_applet_id_version])
        for activity in activities

