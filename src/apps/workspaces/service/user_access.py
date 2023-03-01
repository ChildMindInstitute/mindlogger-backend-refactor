import uuid

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import UserAppletAccess
from apps.applets.domain.applet import AppletPublic
from apps.users import User, UsersCRUD
from apps.workspaces.domain.workspace import PublicWorkspace

__all__ = ["UserAccessService"]


class UserAccessService:
    def __init__(self, user_id: uuid.UUID):
        self._user_id = user_id

    async def get_user_workspaces(self) -> list[PublicWorkspace]:
        """
        Returns the user their current workspaces.
        Workspaces in which the user is the owner or invited user
        """

        accesses: list[
            UserAppletAccess
        ] = await UserAppletAccessCRUD().get_by_user_id(self._user_id)

        workspaces: list[PublicWorkspace] = []

        for access in accesses:
            user_owner: User = await UsersCRUD().get_by_id(access.owner_id)
            workspace = PublicWorkspace(
                owner_id=access.owner_id,
                workspace_name=f"{user_owner.first_name} "
                f"{user_owner.last_name} MindLogger",
            )
            if workspace not in workspaces:
                workspaces.append(workspace)

        return workspaces

    async def get_workspace_applets(self, owner_id: int) -> list[AppletPublic]:
        """Returns the user their chosen workspace applets."""

        accesses: list[
            UserAppletAccess
        ] = await UserAppletAccessCRUD().get_by_user_id(self._user_id)

        applets: list[AppletPublic] = []

        for access in accesses:
            if access.owner_id == owner_id:
                applet: AppletPublic = await AppletsCRUD().get_by_id(
                    access.applet_id
                )
                if applet not in applets:
                    applets.append(applet)

        return applets
