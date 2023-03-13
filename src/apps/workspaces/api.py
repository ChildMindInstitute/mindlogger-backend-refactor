import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.applets.domain.applet import AppletPublic
from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.domain.workspace import (
    PublicWorkspace,
    RemoveManagerAccess,
)
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
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
) -> ResponseMulti[AppletPublic]:
    """Fetch all applets for the specific user and specific workspace."""

    applets: list[AppletPublic] = await UserAccessService(
        user.id
    ).get_workspace_applets(owner_id)

    count: int = await AppletService(
        user.id
    ).get_list_by_single_language_count(deepcopy(query_params))

    return ResponseMulti[AppletPublic](
        count=count,
        result=[AppletPublic.from_orm(applet) for applet in applets],
    )


async def workspace_remove_manager_access(
    user: User = Depends(get_current_user),
    schema: RemoveManagerAccess = Body(...),
):
    """Remove manager access from a specific user."""

    await UserAccessService(user.id).remove_manager_access(schema)
