from pydantic import BaseModel
from pydantic.types import PositiveInt

from apps.applets.domain.constants import Role
from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AppletCreate",
    "AppletUpdate",
    "Applet",
    "PublicApplet",
    "UserAppletAccessCreate",
    "UserAppletAccess",
    "PublicUserAppletAccess",
]


class _AppletBase(BaseModel):
    display_name: str

    def __str__(self) -> str:
        return self.display_name


class PublicApplet(_AppletBase, PublicModel):
    """Public user data model."""

    id: PositiveInt


class AppletCreate(_AppletBase, InternalModel):
    description: str


class AppletUpdate(_AppletBase, InternalModel):
    description: str


class Applet(AppletCreate):
    id: PositiveInt


class UserAppletAccessCreate(InternalModel):
    user_id: PositiveInt
    applet_id: PositiveInt
    role: Role


class UserAppletAccess(UserAppletAccessCreate):
    id: PositiveInt


class PublicUserAppletAccess(PublicModel):
    """Public UserAppletAccess data model."""

    id: PositiveInt
    user_id: PositiveInt
    applet_id: PositiveInt
    role: Role
