from uuid import UUID

from pydantic import EmailStr

from apps.applets.domain import Role
from apps.shared.domain import InternalModel, PublicModel


class Applet(PublicModel):
    id: int
    display_name: str


class InvitationRequest(InternalModel):
    """This model is used to send the invitation request
    to the user for the specific role.
    """

    email: EmailStr
    applet_id: int
    role: Role = Role.RESPONDENT


class Invitation(InternalModel):
    """This is an invitation representation for internal needs."""

    id: int
    email: EmailStr
    applet_id: int
    role: Role
    key: UUID
    status: str
    invitor_id: int


class InvitationDetail(InternalModel):
    id: int
    email: EmailStr
    applet_id: int
    status: str
    applet_name: str
    role: Role
    key: UUID


class InvitationResponse(PublicModel):
    """This model is returned to the user on the invitation request."""

    email: EmailStr
    applet_id: int
    applet_name: str
    role: Role
    key: UUID
    status: str
