import uuid
from uuid import UUID

from pydantic import EmailStr

from apps.applets.domain import Role
from apps.shared.domain import InternalModel, PublicModel


class Applet(PublicModel):
    id: uuid.UUID
    display_name: str


class InvitationRequest(InternalModel):
    """This model is used to send the invitation request
    to the user for the specific role.
    """

    email: EmailStr
    applet_id: uuid.UUID
    role: Role = Role.RESPONDENT
    title: str | None
    body: str | None


class Invitation(InternalModel):
    """This is an invitation representation for internal needs."""

    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    role: Role
    key: UUID
    status: str
    invitor_id: int
    title: str | None
    body: str | None


class InvitationDetail(InternalModel):
    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    status: str
    applet_name: str
    role: Role
    key: UUID
    title: str | None
    body: str | None


class PrivateInvitationDetail(InternalModel):
    id: uuid.UUID
    applet_id: uuid.UUID
    status: str
    applet_name: str
    role: Role
    key: UUID
    title: str | None
    body: str | None


class InvitationResponse(PublicModel):
    """This model is returned to the user on the invitation request."""

    email: EmailStr
    applet_id: uuid.UUID
    applet_name: str
    role: Role
    key: UUID
    status: str
    title: str | None
    body: str | None


class PrivateInvitationResponse(PublicModel):
    applet_id: uuid.UUID
    applet_name: str
    role: Role
    key: UUID
    status: str
    title: str | None
    body: str | None
