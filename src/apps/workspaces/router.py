import uuid

from fastapi.routing import APIRouter
from starlette import status

from apps.applets.api import applet_create
from apps.applets.domain.applet_full import PublicAppletFull
from apps.applets.domain.applets import public_detail
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)
from apps.shared.response import EmptyResponse
from apps.workspaces.api import (
    applet_remove_respondent_access,
    managers_priority_role_retrieve,
    user_workspaces,
    workspace_applet_detail,
    workspace_applet_managers_list,
    workspace_applet_respondent_update,
    workspace_applet_respondents_list,
    workspace_applets,
    workspace_manager_pin,
    workspace_managers_applet_access_list,
    workspace_managers_applet_access_set,
    workspace_managers_list,
    workspace_remove_manager_access,
    workspace_respondent_pin,
    workspace_respondents_list,
    workspace_retrieve,
    workspace_roles_retrieve,
    workspace_users_applet_access_list,
)
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    PublicManagerAppletAccess,
    PublicRespondentAppletAccess,
)
from apps.workspaces.domain.workspace import (
    PublicWorkspace,
    PublicWorkspaceInfo,
    PublicWorkspaceManager,
    PublicWorkspaceRespondent,
    WorkspaceAppletPublic,
    WorkspacePrioritizedRole,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

# User workspaces - "My workspace" and "Shared Workspaces" if exist
router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspace],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicWorkspace]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_workspaces)

router.get(
    "/{owner_id}",
    response_model=Response[PublicWorkspaceInfo],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicWorkspaceInfo]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_retrieve)

router.get(
    "/{owner_id}/priority_role",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[WorkspacePrioritizedRole]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(managers_priority_role_retrieve)

router.get(
    "/{owner_id}/roles",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[dict[uuid.UUID, list[Role]]]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_roles_retrieve)

# Applets in a specific workspace where owner_id is applet owner
router.get(
    "/{owner_id}/applets",
    response_model=ResponseMulti[WorkspaceAppletPublic],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[WorkspaceAppletPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applets)

router.get(
    "/{owner_id}/applets/{applet_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicAppletFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applet_detail)

router.post(
    "/{owner_id}/applets/{applet_id}/respondents/{respondent_id}",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applet_respondent_update)

router.post(
    "/{owner_id}/applets",
    description="""This endpoint is used to create a new applet""",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[public_detail.Applet]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_create)

router.get(
    "/{owner_id}/respondents",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspaceRespondent],
    responses={
        status.HTTP_200_OK: {
            "model": ResponseMulti[PublicWorkspaceRespondent]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_respondents_list)


router.get(
    "/{owner_id}/applets/{applet_id}/respondents",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspaceRespondent],
    responses={
        status.HTTP_200_OK: {
            "model": ResponseMulti[PublicWorkspaceRespondent]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applet_respondents_list)


router.get(
    "/{owner_id}/managers",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspaceManager],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicWorkspaceManager]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_managers_list)

router.get(
    "/{owner_id}/applets/{applet_id}/managers",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspaceManager],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicWorkspaceManager]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applet_managers_list)

router.post(
    "/{owner_id}/respondents/{user_id}/pin",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
    response_class=EmptyResponse,
)(workspace_respondent_pin)


router.post(
    "/{owner_id}/managers/{user_id}/pin",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
    response_class=EmptyResponse,
)(workspace_manager_pin)


router.get(
    "/{owner_id}/respondents/{respondent_id}/accesses",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicRespondentAppletAccess],
    responses={
        status.HTTP_200_OK: {
            "model": ResponseMulti[PublicRespondentAppletAccess]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_users_applet_access_list)

router.get(
    "/{owner_id}/managers/{manager_id}/accesses",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": ResponseMulti[PublicManagerAppletAccess]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_managers_applet_access_list)

router.post(
    "/{owner_id}/managers/{manager_id}/accesses",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_managers_applet_access_set)

# Remove manager access from a specific user
router.post(
    "/removeAccess",
    response_model=None,
    responses={
        status.HTTP_200_OK: {"model": None},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(workspace_remove_manager_access)

applet_router = APIRouter(prefix="/applets", tags=["Applets"])

applet_router.post(
    "/removeAccess",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_remove_respondent_access)
