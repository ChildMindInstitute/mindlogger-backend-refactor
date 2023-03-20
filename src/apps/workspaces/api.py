import uuid
from copy import deepcopy

from fastapi import Depends

from apps.applets.domain.applet import AppletInfoPublic, AppletPublic
from apps.applets.filters import AppletQueryParams
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.domain.workspace import PublicWorkspace
from apps.workspaces.service.user_access import UserAccessService
from infrastructure.http import get_language


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
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
) -> ResponseMulti[AppletPublic]:
    """Fetch all applets for the specific user and specific workspace."""
    query_params.filters["owner_id"] = owner_id

    applets = await UserAccessService(
        user.id
    ).get_workspace_applets_by_language(language, deepcopy(query_params))

    count = await UserAccessService(user.id).get_workspace_applets_count(
        deepcopy(query_params)
    )

    return ResponseMulti(
        result=[AppletInfoPublic.from_orm(applet) for applet in applets],
        count=count,
    )
