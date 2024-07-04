import uuid
from copy import deepcopy

from fastapi import Body, Depends, Query

from apps.answers.deps.preprocess_arbitrary import get_answer_session_by_owner_id
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import PublicAppletFull
from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.invitations.errors import NonUniqueValue
from apps.invitations.services import InvitationsService
from apps.shared.domain import Response, ResponseMulti, ResponseMultiOrdering
from apps.shared.exception import NotFoundError
from apps.shared.query_params import BaseQueryParams, QueryParams, parse_query_params
from apps.subjects.services import SubjectsService
from apps.users.domain import User
from apps.users.services.user import UserService
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import (
    ManagerAccesses,
    PublicRespondentAppletAccess,
    RemoveManagerAccess,
    RespondentInfo,
    RespondentInfoPublic,
)
from apps.workspaces.domain.workspace import (
    AppletIdsQuery,
    PublicWorkspace,
    PublicWorkspaceInfo,
    PublicWorkspaceManager,
    PublicWorkspaceRespondent,
    WorkspaceAppletPublic,
    WorkspacePrioritizedRole,
    WorkspaceSearchAppletPublic,
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

    if user.is_super_admin:
        workspaces = await UserAccessService(session, user.id).get_super_admin_workspaces()
    else:
        workspaces = await UserAccessService(session, user.id).get_user_workspaces()

    return ResponseMulti[PublicWorkspace](
        count=len(workspaces),
        result=[
            PublicWorkspace(
                owner_id=workspace.user_id,
                workspace_name=workspace.workspace_name,
                integrations=workspace.integrations,
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

    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    workspace = await WorkspaceService(session, owner_id).get_workspace(user.id)

    return Response(result=PublicWorkspaceInfo.from_orm(workspace))


async def managers_priority_role_retrieve(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    appletIDs: AppletIdsQuery = Depends(),
    session=Depends(get_session),
) -> Response[WorkspacePrioritizedRole]:
    """Fetch all workspaces for the specific user."""
    if user.is_super_admin:
        return Response(result=WorkspacePrioritizedRole(role=Role.SUPER_ADMIN))
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    await CheckAccessService(session, user.id).check_workspace_access(owner_id)
    role = await WorkspaceService(session, user.id).get_applets_roles_by_priority(owner_id, appletIDs.applet_ids)

    return Response(result=WorkspacePrioritizedRole(role=role))


async def workspace_roles_retrieve(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    applet_ids: list[uuid.UUID] | None = Query(None, alias="appletIds"),
    session=Depends(get_session),
) -> Response[dict[uuid.UUID, list[Role]]]:
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    applet_roles = await UserAccessService(session, user.id).get_workspace_applet_roles(
        owner_id, applet_ids, user.is_super_admin
    )

    return Response(result=applet_roles)


async def workspace_folder_applets(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> ResponseMulti[WorkspaceAppletPublic]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)
    if not user.is_super_admin:
        await CheckAccessService(session, user.id).check_workspace_access(owner_id)
        await UserAccessService(session, user.id).check_access(owner_id)
    applets = await service.get_workspace_folder_applets(owner_id, folder_id, language)

    return ResponseMulti(
        result=[WorkspaceAppletPublic.from_orm(applet) for applet in applets],
        count=len(applets),
    )


async def workspace_applets(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(get_session),
) -> ResponseMulti[WorkspaceAppletPublic]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)
    if not user.is_super_admin:
        await CheckAccessService(session, user.id).check_workspace_access(owner_id)
        await UserAccessService(session, user.id).check_access(owner_id)
    applets = await service.get_workspace_applets(owner_id, language, deepcopy(query_params))

    count = await service.get_workspace_applets_count(owner_id, query_params)

    return ResponseMulti(
        result=[WorkspaceAppletPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def search_workspace_applets(
    owner_id: uuid.UUID,
    text: str,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(get_session),
) -> ResponseMulti[WorkspaceSearchAppletPublic]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)
    if not user.is_super_admin:
        await CheckAccessService(session, user.id).check_workspace_access(owner_id)
        await UserAccessService(session, user.id).check_access(owner_id)
    applets = await service.search_workspace_applets(owner_id, text, language, deepcopy(query_params))

    count = await service.search_workspace_applets_count(owner_id, text)

    return ResponseMulti(
        result=[WorkspaceSearchAppletPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def workspace_applet_detail(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicAppletFull]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    await CheckAccessService(session, user.id).check_workspace_applet_detail_access(applet_id)
    applet = await AppletService(session, user.id).get_full_applet(applet_id)

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
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
        subject_service = SubjectsService(session, user.id)
        subject = await subject_service.get_by_user_and_applet(respondent_id, applet_id)
        if not subject:
            raise NotFoundError()
        assert subject.id
        exist = await subject_service.check_secret_id(subject.id, schema.secret_user_id, applet_id)
        if exist:
            raise NonUniqueValue()
        await subject_service.update(subject.id, **schema.dict(by_alias=False))


async def workspace_remove_manager_access(
    user: User = Depends(get_current_user),
    schema: RemoveManagerAccess = Body(...),
    session=Depends(get_session),
):
    """Remove manager access from a specific user."""
    async with atomic(session):
        await UserAccessService(session, user.id).remove_manager_access(schema)
        # Get applets where user still have access
        ex_admin = await UserService(session).get(schema.user_id)
        if ex_admin:
            management_applets = await UserAccessService(session, schema.user_id).get_management_applets(
                schema.applet_ids
            )
            ids_to_remove = set(schema.applet_ids) - set(management_applets)
            await InvitationsService(session, ex_admin).delete_for_managers(list(ids_to_remove))


async def workspace_respondents_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(WorkspaceUsersQueryParams)),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session_by_owner_id),
) -> ResponseMultiOrdering[PublicWorkspaceRespondent]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(session, user.id).check_workspace_respondent_list_access(owner_id)

    data, total, ordering_fields = await service.get_workspace_respondents(owner_id, None, deepcopy(query_params))
    respondents = await AnswerService(
        session=session, arbitrary_session=answer_session
    ).fill_last_activity_workspace_respondent(data)
    respondents = await InvitationsService(session, user).fill_pending_invitations_respondents(respondents)
    return ResponseMultiOrdering(result=respondents, count=total, ordering_fields=ordering_fields)


async def workspace_applet_respondents_list(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(WorkspaceUsersQueryParams)),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session_by_owner_id),
) -> ResponseMulti[PublicWorkspaceRespondent]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(session, user.id).check_applet_respondent_list_access(applet_id)

    data, total, ordering_fields = await service.get_workspace_respondents(owner_id, applet_id, deepcopy(query_params))
    respondents = await AnswerService(
        session=session, arbitrary_session=answer_session
    ).fill_last_activity_workspace_respondent(data, applet_id)
    respondents = await InvitationsService(session, user).fill_pending_invitations_respondents(respondents)
    return ResponseMultiOrdering(result=respondents, count=total, ordering_fields=ordering_fields)


async def workspace_managers_list(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(WorkspaceUsersQueryParams)),
    session=Depends(get_session),
) -> ResponseMultiOrdering[PublicWorkspaceManager]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(session, user.id).check_workspace_manager_list_access(owner_id)

    data, total, ordering_fields = await service.get_workspace_managers(owner_id, None, deepcopy(query_params))
    workspaces_manager = []
    for workspace_manager in data:
        workspaces_manager.append(
            PublicWorkspaceManager(
                id=workspace_manager.id,
                first_name=workspace_manager.first_name,
                last_name=workspace_manager.last_name,
                email=workspace_manager.email_encrypted,
                roles=workspace_manager.roles,
                created_at=workspace_manager.created_at,
                last_seen=workspace_manager.last_seen,
                is_pinned=workspace_manager.is_pinned,
                applets=workspace_manager.applets,
                title=workspace_manager.title,
                titles=workspace_manager.titles,
                status=workspace_manager.status,
            )
        )
    return ResponseMultiOrdering(result=workspaces_manager, count=total, ordering_fields=ordering_fields)


async def workspace_applet_managers_list(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(WorkspaceUsersQueryParams)),
    session=Depends(get_session),
) -> ResponseMultiOrdering[PublicWorkspaceManager]:
    service = WorkspaceService(session, user.id)
    await service.exists_by_owner_id(owner_id)

    await CheckAccessService(session, user.id).check_applet_manager_list_access(applet_id)

    data, total, ordering_fields = await service.get_workspace_managers(owner_id, applet_id, deepcopy(query_params))
    workspaces_manager = []
    for workspace_manager in data:
        workspaces_manager.append(
            PublicWorkspaceManager(
                id=workspace_manager.id,
                first_name=workspace_manager.first_name,
                last_name=workspace_manager.last_name,
                email=workspace_manager.email_encrypted,
                roles=workspace_manager.roles,
                created_at=workspace_manager.created_at,
                last_seen=workspace_manager.last_seen,
                is_pinned=workspace_manager.is_pinned,
                applets=workspace_manager.applets,
                title=workspace_manager.title,
                titles=workspace_manager.titles,
                status=workspace_manager.status,
                invitation_key=workspace_manager.invitation_key,
            )
        )
    return ResponseMultiOrdering(result=workspaces_manager, count=total, ordering_fields=ordering_fields)


async def workspace_respondent_pin(
    owner_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await UserAccessService(session, user.id).pin(owner_id, UserPinRole.respondent, user_id=user_id)


async def workspace_subject_pin(
    owner_id: uuid.UUID,
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await UserAccessService(session, user.id).pin(owner_id, UserPinRole.respondent, subject_id=subject_id)


async def workspace_manager_pin(
    owner_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
        await UserAccessService(session, user.id).pin(owner_id, UserPinRole.manager, user_id)


async def workspace_users_applet_access_list(
    owner_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(BaseQueryParams)),
) -> ResponseMulti[PublicRespondentAppletAccess]:
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    service = UserAccessService(session, user.id)
    accesses = await service.get_respondent_accesses_by_workspace(owner_id, respondent_id, query_params)
    count = await service.get_respondent_accesses_by_workspace_count(owner_id, respondent_id)

    return ResponseMulti(
        result=[PublicRespondentAppletAccess.from_orm(access) for access in accesses],
        count=count,
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
        await AppletService(session, user.id).exist_by_ids([access.applet_id for access in accesses.accesses])
        await CheckAccessService(session, user.id).check_workspace_manager_accesses_access(owner_id)
        await UserService(session).exists_by_id(manager_id)

        await UserAccessService(session, user.id).set(owner_id, manager_id, accesses)


async def workspace_applet_get_respondent(
    owner_id: uuid.UUID,
    applet_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session_by_owner_id),
) -> Response[RespondentInfoPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await WorkspaceService(session, user.id).exists_by_owner_id(owner_id)
    await CheckAccessService(session, user.id).check_applet_respondent_list_access(applet_id)

    respondent_info = await UserAppletAccessService(session, user.id, applet_id).get_respondent_info(
        respondent_id, applet_id, owner_id
    )
    # get last activity time
    result = await AnswerService(session=session, arbitrary_session=answer_session).get_last_answer_dates(
        [respondent_info.subject_id],
        applet_id,
    )
    respondent_info.last_seen = result.get(respondent_info.subject_id)
    return Response(result=respondent_info)
