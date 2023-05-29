import uuid
from copy import deepcopy

from fastapi import Body, Depends, Query

from apps.applets.domain.applet_full import PublicAppletFull
from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import (
    BaseQueryParams,
    QueryParams,
    parse_query_params,
)
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import (
    ManagerAccesses,
    PublicManagerAppletAccess,
    PublicRespondentAppletAccess,
    RemoveManagerAccess,
    RemoveRespondentAccess,
    RespondentInfo,
)
from apps.workspaces.domain.workspace import (
    PublicWorkspace,
    PublicWorkspaceInfo,
    PublicWorkspaceManager,
    PublicWorkspaceRespondent,
    WorkspaceAppletPublic,
    WorkspacePrioritizedRole,
)
from apps.workspaces.filters import WorkspaceUsersQueryParams
from apps.workspaces.service.check_access import CheckAccessService
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session
from infrastructure.http import get_language


async def user_workspaces(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[PublicWorkspace]:
    """Fetch all workspaces for the specific user."""

    async with atomic(session):
        if user.is_super_admin:
            workspaces = await UserAccessService(
                session, user.id
            ).get_super_admin_workspaces()
        else:
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
    session=Depends(get_session),
) -> Response[PublicWorkspaceInfo]:
    """Fetch all workspaces for the specific user."""

    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        workspace = await WorkspaceService(session, owner_id).get_workspace(
            user.id
        )

    return Response(result=PublicWorkspaceInfo.from_orm(workspace))


async def managers_priority_role_retrieve(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    appletIDs: str = "",
    session=Depends(get_session),
) -> Response[WorkspacePrioritizedRole]:
    """Fetch all workspaces for the specific user."""
    if user.is_super_admin:
        return Response(result=WorkspacePrioritizedRole(role=Role.SUPER_ADMIN))

    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        applet_ids = list(map(uuid.UUID, filter(None, appletIDs.split(","))))
        role = await UserAppletAccessCRUD(
            session
        ).get_applets_roles_by_priority_for_workspace(
            owner_id, user.id, applet_ids
        )

    return Response(result=WorkspacePrioritizedRole(role=role))


async def workspace_roles_retrieve(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    applet_ids: list[uuid.UUID] | None = Query(None, alias="appletIds"),
    session=Depends(get_session),
) -> Response[dict[uuid.UUID, list[Role]]]:
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    applet_roles = await UserAccessService(
        session, user.id
    ).get_workspace_applet_roles(owner_id, applet_ids)

    return Response(result=applet_roles)


async def workspace_applets(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(get_session),
) -> ResponseMulti[WorkspaceAppletPublic]:
    """Fetch all applets for the specific user and specific workspace."""
    query_params.filters["owner_id"] = owner_id

    async with atomic(session):
        service = WorkspaceService(session, user.id)
        await service.exists_by_owner_id(owner_id)
        await CheckAccessService(session, user.id).check_workspace_access(
            owner_id
        )
        await UserAccessService(session, user.id).check_access(owner_id)
        applets = await service.get_workspace_applets(
            language, deepcopy(query_params)
        )

        count = await UserAccessService(
            session, user.id
        ).get_workspace_applets_count(deepcopy(query_params))

    return ResponseMulti(
        result=[WorkspaceAppletPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def workspace_applet_detail(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicAppletFull]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        applet = await AppletService(session, user.id).get_full_applet(
            applet_id
        )

    return Response(result=PublicAppletFull.from_orm(applet))


async def workspace_applet_respondent_update(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    respondent_id: uuid.UUID,
    schema: RespondentInfo = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        await UserAppletAccessService(session, user.id, applet_id).update_meta(
            respondent_id, Role.RESPONDENT, **schema.dict(by_alias=True)
        )


async def workspace_remove_manager_access(
    user: User = Depends(get_current_user),
    schema: RemoveManagerAccess = Body(...),
    session=Depends(get_session),
):
    """Remove manager access from a specific user."""
    async with atomic(session):
        await UserAccessService(session, user.id).remove_manager_access(schema)


async def applet_remove_respondent_access(
    user: User = Depends(get_current_user),
    schema: RemoveRespondentAccess = Body(...),
    session=Depends(get_session),
):
    async with atomic(session):
        await UserAccessService(session, user.id).remove_respondent_access(
            schema
        )


async def workspace_respondents_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[PublicWorkspaceRespondent]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(
        session, user.id
    ).check_workspace_respondent_list_access(owner_id)

    data, total = await service.get_workspace_respondents(
        owner_id, None, deepcopy(query_params)
    )

    return ResponseMulti(result=data, count=total)


async def workspace_applet_respondents_list(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[PublicWorkspaceRespondent]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(
        session, user.id
    ).check_applet_respondent_list_access(applet_id)

    data, total = await service.get_workspace_respondents(
        owner_id, applet_id, deepcopy(query_params)
    )

    return ResponseMulti(result=data, count=total)


async def workspace_managers_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[PublicWorkspaceManager]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(
        session, user.id
    ).check_workspace_manager_list_access(owner_id)

    data, total = await service.get_workspace_managers(
        owner_id, None, deepcopy(query_params)
    )

    return ResponseMulti(result=data, count=total)


async def workspace_applet_managers_list(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(WorkspaceUsersQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[PublicWorkspaceManager]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(
        session, user.id
    ).check_applet_manager_list_access(applet_id)

    data, total = await service.get_workspace_managers(
        owner_id, applet_id, deepcopy(query_params)
    )

    return ResponseMulti(result=data, count=total)


async def workspace_respondent_pin(
    owner_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await UserAccessService(session, user.id).pin(
            owner_id, user_id, UserPinRole.respondent
        )


async def workspace_manager_pin(
    owner_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await UserAccessService(session, user.id).pin(
            owner_id, user_id, UserPinRole.manager
        )


async def workspace_users_applet_access_list(
    owner_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(BaseQueryParams)),
) -> ResponseMulti[PublicRespondentAppletAccess]:
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        service = UserAccessService(session, user.id)
        accesses = await service.get_respondent_accesses_by_workspace(
            owner_id, respondent_id, query_params
        )
        count = await service.get_respondent_accesses_by_workspace_count(
            owner_id, respondent_id
        )

    return ResponseMulti(
        result=[
            PublicRespondentAppletAccess.from_orm(access)
            for access in accesses
        ],
        count=count,
    )


async def workspace_managers_applet_access_list(
    owner_id: uuid.UUID,
    manager_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[PublicManagerAppletAccess]:
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await CheckAccessService(
            session, user.id
        ).check_workspace_manager_accesses_access(owner_id)

        service = UserAccessService(session, user.id)
        accesses = await service.get_manager_accesses(owner_id, manager_id)

    return ResponseMulti(
        result=[
            PublicManagerAppletAccess.from_orm(access) for access in accesses
        ],
        count=len(accesses),
    )


async def workspace_managers_applet_access_set(
    owner_id: uuid.UUID,
    manager_id: uuid.UUID,
    accesses: ManagerAccesses = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await CheckAccessService(
            session, user.id
        ).check_workspace_manager_accesses_access(owner_id)

        await UserAccessService(session, user.id).set(
            owner_id, manager_id, accesses
        )
