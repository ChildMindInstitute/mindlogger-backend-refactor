import datetime
import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "PublicWorkspace",
    "UserWorkspace",
    "WorkspaceUser",
    "PublicWorkspaceUser",
]


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


class WorkspaceUser(InternalModel):
    id: uuid.UUID
    nickname: str | None
    roles: list[str]
    secret_id: str | None
    last_seen: datetime.datetime


class PublicWorkspaceUser(PublicModel):
    id: uuid.UUID
    nickname: str | None
    roles: list[str]
    secret_id: str | None
    last_seen: datetime.datetime
