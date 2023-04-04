from fastapi.routing import APIRouter
from starlette import status

from apps.applets.domain.applet import AppletInfoPublic
from apps.shared.domain import ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)
from apps.workspaces.api import (
    applet_remove_respondent_access,
    user_workspaces,
    workspace_applets,
    workspace_remove_manager_access,
    workspace_users_list,
    workspace_users_pin,
)
from apps.workspaces.domain.workspace import (
    PublicWorkspace,
    PublicWorkspaceUser,
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

# Applets in a specific workspace where owner_id is applet owner
router.get(
    "/{owner_id}/applets",
    response_model=ResponseMulti[AppletInfoPublic],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AppletInfoPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_applets)

router.get(
    "/{owner_id}/users",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicWorkspaceUser],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicWorkspaceUser]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_users_list)

router.post(
    "/{owner_id}/users/pin",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(workspace_users_pin)

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
