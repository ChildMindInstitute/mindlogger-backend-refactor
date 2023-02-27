from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel
from apps.workspaces.domain.constants import Role

__all__ = [
    "UserAppletAccessCreate",
    "UserAppletAccess",
    "PublicUserAppletAccess",
    "UserAppletAccessItem",
]


class UserAppletAccessCreate(InternalModel):
    user_id: PositiveInt
    applet_id: PositiveInt
    role: Role
    owner_id: PositiveInt
    invitor_id: PositiveInt
    meta: dict


class UserAppletAccess(UserAppletAccessCreate):
    id: PositiveInt


class PublicUserAppletAccess(PublicModel):
    """Public UserAppletAccess data model."""

    id: PositiveInt
    user_id: PositiveInt
    applet_id: PositiveInt
    role: Role


class UserAppletAccessItem(InternalModel):
    """This is an UserAppletAccess representation for internal needs."""

    user_id: PositiveInt
    applet_id: PositiveInt
    role: Role
