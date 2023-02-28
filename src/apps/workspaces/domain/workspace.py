from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import PublicModel

__all__ = [
    "PublicWorkspace",
]


class PublicWorkspace(PublicModel):
    """This model is returned to the user their current workspace."""

    owner_id: PositiveInt = Field(
        description="This field represents the applet owner id",
    )
    workspace_name: str = Field(
        description="This field represents the name of workspace "
        "which is consists of 'first name', 'last name' of user "
        "which is applet owner and 'MindLogger'",
    )
