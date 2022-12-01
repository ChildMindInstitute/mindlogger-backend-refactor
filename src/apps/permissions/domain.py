from pydantic import BaseModel, EmailStr
from pydantic.types import PositiveInt

from apps.permissions.db import Role
from apps.shared.domain import BaseError, InternalModel, PublicModel

__all__ = [
    "UserAppletAccessCreate",
    "UserAppletAccess",
    "PublicUserAppletAccess",
]


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
