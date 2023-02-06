from apps.applets.crud import AppletsCRUD
from apps.applets.domain import AppletFolder
from apps.applets.domain.applets.fetch import Applet
from apps.applets.errors import AppletAccessDenied, AppletsFolderAccessDenied
from apps.applets.service.user_applet_access import UserAppletAccessService
from apps.folders.crud import FolderCRUD

__all__ = ["AppletService"]


class AppletService:
    INITIAL_VERSION = "1.0.0"
    VERSION_DIFFERENCE = 1

    # TODO: implement applet create/update logics here

    def __init__(self, creator_id: int):
        self._creator_id = creator_id

    def get_next_version(self, version: str | None = None):
        if not version:
            return self.INITIAL_VERSION
        return ".".join(
            list(str(int(version.replace(".", "")) + self.VERSION_DIFFERENCE))
        )

    def get_prev_version(self, version: str):
        int_version = int(version.replace(".", ""))
        if int_version < int(self.INITIAL_VERSION.replace(".", "")):
            return self.INITIAL_VERSION
        return ".".join(list(str(int_version - self.VERSION_DIFFERENCE)))

    async def exist_by_id(self, applet_id: int) -> bool:
        return await AppletsCRUD().exist_by_id(applet_id)

    async def delete_applet_by_id(self, applet_id: int):
        await self._validate_delete_applet(self._creator_id, applet_id)
        await AppletsCRUD().delete_by_id(applet_id)

    async def _validate_delete_applet(self, user_id, applet_id):
        role = await UserAppletAccessService(
            user_id, applet_id
        ).get_admins_role()
        if not role:
            raise AppletAccessDenied()

    async def get_folder_applets(self, folder_id: int) -> list[Applet]:
        schemas = await AppletsCRUD().get_folder_applets(
            self._creator_id, folder_id
        )
        return [Applet.from_orm(schema) for schema in schemas]

    async def set_applet_folder(self, schema: AppletFolder):
        if schema.folder_id:
            await self._move_to_folder(schema.applet_id, schema.folder_id)
        else:
            await self._remove_from_folder(schema.applet_id)

    async def _move_to_folder(self, applet_id: int, folder_id: int):
        await self._validate_applet(applet_id)
        await self._validate_folder(folder_id)
        await AppletsCRUD().set_applets_folder(applet_id, folder_id)

    async def _remove_from_folder(self, applet_id: int):
        await self._validate_applet(applet_id)
        await AppletsCRUD().set_applets_folder(applet_id, None)

    async def _validate_applet(self, applet_id: int):
        applet_schema = await AppletsCRUD().get_by_id(applet_id)
        if applet_schema.creator_id != self._creator_id:
            raise AppletAccessDenied()

    async def _validate_folder(self, folder_id: int):
        folder = await FolderCRUD().get_by_id(folder_id)

        if folder.creator_id != self._creator_id:
            raise AppletsFolderAccessDenied()
