import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel
from apps.workspaces.domain.constants import Role

__all__ = [
    "UserAppletAccessCreate",
    "UserAppletAccess",
    "PublicUserAppletAccess",
    "UserAppletAccessItem",
    "RemoveRespondentAccess",
]


class UserAppletAccessCreate(InternalModel):
    user_id: uuid.UUID
    applet_id: uuid.UUID
    role: Role
    owner_id: uuid.UUID
    invitor_id: uuid.UUID
    meta: dict


class UserAppletAccess(UserAppletAccessCreate):
    id: uuid.UUID


class PublicUserAppletAccess(PublicModel):
    """Public UserAppletAccess data model."""

    id: uuid.UUID
    user_id: uuid.UUID
    applet_id: uuid.UUID
    role: Role


class UserAppletAccessItem(InternalModel):
    """This is an UserAppletAccess representation for internal needs."""

    user_id: uuid.UUID
    applet_id: uuid.UUID
    role: Role


class RemoveRespondentAccess(InternalModel):
    """Respondent access removal model."""

    user_id: uuid.UUID = Field(
        description="This field represents the applet respondent id",
    )
    applet_ids: list[uuid.UUID] = Field(
        description="This field represents the applet ids",
    )
    delete_responses: bool = Field(
        description="This field represents the flag for deleting responses",
    )
