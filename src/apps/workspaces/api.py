import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.applets.domain.applet import AppletInfoPublic, AppletPublic
from apps.applets.domain.applet_full import PublicAppletFull
from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.domain.user_applet_access import (
    PinUser,
    RemoveManagerAccess,
    RemoveRespondentAccess,
)
from apps.workspaces.domain.workspace import (
    PublicWorkspace,
    PublicWorkspaceInfo,
    PublicWorkspaceManager,
    PublicWorkspaceRespondent,
)
from apps.workspaces.filters import WorkspaceUsersQueryParams
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic, session_manager
from infrastructure.http import get_language


async def user_workspaces(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicWorkspace]:
    """Fetch all workspaces for the specific user."""

    async with atomic(session):
        workspaces = await UserAccessService(
            session, user.id
        ).get_user_workspaces()

    return ResponseMulti[PublicWorkspace](
        count=len(workspaces),
        result=[
            PublicWorkspace(
                owner_id=workspace.user_id,
                workspace_name=workspace.workspace_name,
            )
            for workspace in workspaces
        ],
    )


async def workspace_retrieve(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicWorkspaceInfo]:
    """Fetch all workspaces for the specific user."""

    async with atomic(session):
        workspace = await WorkspaceService(session, owner_id).get_workspace(
            user.id
        )

    return Response(result=PublicWorkspaceInfo.from_orm(workspace))


async def workspace_applets(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[AppletPublic]:
    """Fetch all applets for the specific user and specific workspace."""
    query_params.filters["owner_id"] = owner_id

    async with atomic(session):
        # TODO: enable when it is needed
        # await UserAccessService(session, user.id).check_access(owner_id)
        applets = await UserAccessService(
            session, user.id
        ).get_workspace_applets_by_language(language, deepcopy(query_params))

        count = await UserAccessService(
            session, user.id
        ).get_workspace_applets_count(deepcopy(query_params))

    return ResponseMulti(
        result=[AppletInfoPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def workspace_applet_detail(
    owner_id: uuid.UUID,
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicAppletFull]:
    async with atomic(session):
        applet = await AppletService(session, user.id).get_full_applet(id_)

    return Response(result=PublicAppletFull.from_orm(applet))


async def workspace_remove_manager_access(
    user: User = Depends(get_current_user),
    schema: RemoveManagerAccess = Body(...),
    session=Depends(session_manager.get_session),
):
    """Remove manager access from a specific user."""

    await UserAccessService(session, user.id).remove_manager_access(schema)


async def applet_remove_respondent_access(
    user: User = Depends(get_current_user),
    schema: RemoveRespondentAccess = Body(...),
    session=Depends(session_manager.get_session),
):
    await UserAccessService(session, user.id).remove_respondent_access(schema)


async def workspace_respondents_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicWorkspaceRespondent]:
    async with atomic(session):
        users = await WorkspaceService(
            session, user.id
        ).get_workspace_respondents(owner_id, deepcopy(query_params))
        count = await WorkspaceService(
            session, user.id
        ).get_workspace_respondents_count(owner_id, deepcopy(query_params))
    return ResponseMulti(
        count=count,
        result=[PublicWorkspaceRespondent.from_orm(user) for user in users],
    )


async def workspace_managers_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicWorkspaceManager]:
    async with atomic(session):
        users = await WorkspaceService(
            session, user.id
        ).get_workspace_managers(owner_id, deepcopy(query_params))
        count = await WorkspaceService(
            session, user.id
        ).get_workspace_managers_count(owner_id, deepcopy(query_params))
    return ResponseMulti(
        count=count,
        result=[PublicWorkspaceManager.from_orm(user) for user in users],
    )


async def workspace_users_pin(
    owner_id: uuid.UUID,
    data: PinUser,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await UserAccessService(session, user.id).pin(data.access_id)
