import datetime
import uuid

from pydantic import Field

from apps.applets.domain.applet import (
    AppletSingleLanguageInfo,
    AppletSingleLanguageInfoPublic,
)
from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicWorkspace",
    "UserWorkspace",
    "WorkspaceRespondent",
    "PublicWorkspaceRespondent",
    "WorkspaceManager",
    "PublicWorkspaceManager",
    "WorkspaceInfo",
    "PublicWorkspaceInfo",
]

from apps.workspaces.domain.constants import Role


class PublicWorkspace(PublicModel):
    """This model is returned to the user their current workspace."""

    owner_id: uuid.UUID = Field(
        description="This field represents the applet owner id",
    )
    workspace_name: str = Field(
        description="This field represents the name of workspace "
        "which is consists of 'first name', 'last name' of user "
        "which is applet owner and prefix",
    )


class UserWorkspace(InternalModel):
    """This model used for internal needs, returned to the user
    their current workspace.
    """

    user_id: uuid.UUID = Field(
        description="This field represents the applet owner id",
    )
    workspace_name: str = Field(
        description="This field represents the name of workspace "
        "which is consists of 'first name', 'last name' of user "
        "which is applet owner and prefix",
    )


class WorkspaceRespondentDetails(InternalModel):
    applet_id: uuid.UUID
    applet_display_name: str
    access_id: uuid.UUID
    respondent_nickname: str | None = None
    respondent_secret_id: str | None = None
    has_individual_schedule: bool = False


class WorkspaceRespondent(InternalModel):
    id: uuid.UUID
    nicknames: list[str] | None = None
    secret_ids: list[str] | None = None
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceRespondentDetails] | None = None


class WorkspaceManagerDetails(InternalModel):
    applet_id: uuid.UUID
    applet_display_name: str
    access_id: uuid.UUID
    role: Role


class WorkspaceManager(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    roles: list[Role]
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceManagerDetails] | None = None


class PublicWorkspaceRespondent(PublicModel):
    id: uuid.UUID
    nicknames: list[str] | None
    secret_ids: list[str] | None
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceRespondentDetails] | None = None


class PublicWorkspaceManager(PublicModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    roles: list[Role]
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceManagerDetails] | None = None


class WorkspaceInfo(InternalModel):
    name: str
    has_managers: bool


class PublicWorkspaceInfo(PublicModel):
    name: str
    has_managers: bool


class WorkspaceApplet(AppletSingleLanguageInfo):
    role: Role = Role.RESPONDENT


class WorkspaceAppletPublic(AppletSingleLanguageInfoPublic):
    role: Role


class WorkspacePrioritizedRole(PublicModel):
    role: Role
