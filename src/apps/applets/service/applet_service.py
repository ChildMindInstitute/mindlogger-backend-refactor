__all__ = ["AppletService"]

from apps.applets.crud import AppletsCRUD
from apps.applets.errors import DoesNotHaveAccess
from apps.applets.service.user_applet_access import UserAppletAccessService


class AppletService:
    INITIAL_VERSION = "1.0.0"
    VERSION_DIFFERENCE = 1

    # TODO: implement applet create/update logics here

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

    async def delete_applet_by_id(self, user_id, applet_id: int):
        await self._validate_delete_applet(user_id, applet_id)
        await AppletsCRUD().delete_by_id(applet_id)

    async def _validate_delete_applet(self, user_id, applet_id):
        role = await UserAppletAccessService(user_id, applet_id).is_admin()
        if not role:
            raise DoesNotHaveAccess(
                message="You do not have access to delete applet."
            )
