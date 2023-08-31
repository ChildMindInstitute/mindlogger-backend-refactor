import datetime
import uuid

from pydantic import Field, validator

from apps.applets.domain.base import Encryption
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

from apps.shared.encryption import decrypt
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

    @property
    def plain_workspace_name(self) -> str | None:
        if self.workspace_name:
            return decrypt(bytes.fromhex(self.workspace_name)).decode("utf-8")
        return None


class WorkspaceAppletEncryption(InternalModel):
    public_key: str
    prime: str
    base: str
    account_id: str


class WorkspaceRespondentDetails(InternalModel):
    applet_id: uuid.UUID
    applet_display_name: str
    applet_image: str | None
    access_id: uuid.UUID
    respondent_nickname: str | None = None
    respondent_secret_id: str | None = None
    has_individual_schedule: bool = False
    encryption: WorkspaceAppletEncryption | None = None


class WorkspaceRespondent(InternalModel):
    id: uuid.UUID
    nicknames: list[str] | None = None
    secret_ids: list[str] | None = None
    is_anonymous_respondent: bool
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceRespondentDetails] | None = None


class AppletRole(InternalModel):
    access_id: uuid.UUID
    role: Role


class WorkspaceManagerApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    roles: list[AppletRole]
    encryption: WorkspaceAppletEncryption


def group_applet_roles(value):
    applets = {}
    for applet_role in value:
        applet_id = applet_role["applet_id"]
        applet = applets.get(applet_id)
        if not applet:
            applet = {
                "id": applet_id,
                "display_name": applet_role["applet_display_name"],
                "roles": [],
            }
        applet["roles"].append(
            dict(access_id=applet_role["access_id"], role=applet_role["role"])
        )
        applets[applet_id] = applet

    return list(applets.values())


class WorkspaceManager(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    roles: list[Role]
    reviewer_respondents: list[uuid.UUID]
    last_seen: datetime.datetime
    is_pinned: bool = False
    applets: list[WorkspaceManagerApplet] | None = None

    @validator("applets", pre=True)
    def group_applets(cls, value):
        applets = {}
        for applet_role in value:
            applet_id = applet_role["applet_id"]
            applet = applets.get(applet_id)
            if not applet:
                applet = {
                    "id": applet_id,
                    "display_name": applet_role["applet_display_name"],
                    "image": applet_role["applet_image"],
                    "roles": [],
                    "encryption": applet_role["encryption"],
                }
            applet["roles"].append(
                dict(
                    access_id=applet_role["access_id"],
                    role=applet_role["role"],
                )
            )
            applets[applet_id] = applet

        return list(applets.values())

    @property
    def plain_first_name(self) -> str | None:
        if self.first_name:
            return decrypt(bytes.fromhex(self.first_name)).decode("utf-8")
        return None

    @property
    def plain_last_name(self) -> str | None:
        if self.last_name:
            return decrypt(bytes.fromhex(self.last_name)).decode("utf-8")
        return None


class PublicWorkspaceRespondent(PublicModel):
    id: uuid.UUID
    nicknames: list[str] | None
    secret_ids: list[str] | None
    is_anonymous_respondent: bool
    last_seen: datetime.datetime
    is_pinned: bool = False
    details: list[WorkspaceRespondentDetails] | None = None


class PublicWorkspaceManager(PublicModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    roles: list[Role]
    reviewer_respondents: list[uuid.UUID]
    last_seen: datetime.datetime
    is_pinned: bool = False
    applets: list[WorkspaceManagerApplet] | None = None


class WorkspaceInfo(InternalModel):
    name: str
    has_managers: bool


class PublicWorkspaceInfo(PublicModel):
    name: str
    has_managers: bool


class WorkspaceApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folders_applet_count: int
    description: dict | None
    activity_count: int | None


class WorkspaceSearchApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folder_id: uuid.UUID | None
    folder_name: str | None


class WorkspaceAppletPublic(PublicModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None
    type: str
    folders_applet_count: int
    description: dict | None
    activity_count: int | None


class WorkspaceSearchAppletPublic(PublicModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folder_id: uuid.UUID | None
    folder_name: str | None


class WorkspacePrioritizedRole(PublicModel):
    role: Role | None


class AppletRoles(InternalModel):
    applet_id: uuid.UUID
    roles: list[Role]
