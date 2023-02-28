from fastapi import Depends

from apps.applets.domain.applet import AppletPublic
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.users.domain import User
from apps.workspaces.domain.workspace import PublicWorkspace
from apps.workspaces.service.user_access import UserAccessService


async def user_workspaces(
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicWorkspace]:
    """Fetch all workspaces for the specific user."""

    workspaces: list[PublicWorkspace] = await UserAccessService(
        user.id
    ).get_user_workspaces()

    return ResponseMulti[PublicWorkspace](
        count=len(workspaces),
        result=[
            PublicWorkspace(**workspace.dict()) for workspace in workspaces
        ],
    )


async def workspace_applets(
    owner_id: int, user: User = Depends(get_current_user)
) -> ResponseMulti[AppletPublic]:
    """Fetch all applets for the specific user and specific workspace."""

    applets: list[AppletPublic] = await UserAccessService(
        user.id
    ).get_workspace_applets(owner_id)

    return ResponseMulti[AppletPublic](
        count=len(applets),
        result=[AppletPublic.from_orm(applet) for applet in applets],
    )
