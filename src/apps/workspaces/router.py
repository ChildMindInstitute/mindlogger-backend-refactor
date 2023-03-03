from fastapi.routing import APIRouter
from starlette import status

from apps.applets.domain.applet import AppletPublic
from apps.shared.domain import ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)
from apps.workspaces.api import user_workspaces, workspace_applets
from apps.workspaces.domain.workspace import PublicWorkspace

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
    "/{owner_id}",
    response_model=ResponseMulti[AppletPublic],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AppletPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(workspace_applets)
