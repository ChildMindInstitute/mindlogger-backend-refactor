from uuid import UUID

from pydantic import EmailStr, Field

from apps.applets.domain import ManagersRole, Role
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


class InvitationRespondentRequest(InternalModel):
    """This model is used to send the invitation request
    to the user for the respondent roles.
    """

    email: EmailStr
    first_name: str
    last_name: str
    secret_user_id: str
    nickname: str
    language: str = Field(max_length=2)


class InvitationManagersRequest(InternalModel):
    """This model is used to send the invitation request
    to the user for managers roles - "manager", "coordinator", "editor".
    """

    email: EmailStr
    first_name: str
    last_name: str
    role: ManagersRole
    language: str = Field(max_length=2)


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


class InvitationDetailForRespondent(InternalModel):
    id: int
    secret_user_id: str
    nickname: str
    applet_id: int
    status: str
    applet_name: str
    role: Role = Role.RESPONDENT
    key: UUID


class InvitationDetailForManagers(InternalModel):
    id: int
    email: EmailStr
    applet_id: int
    status: str
    applet_name: str
    role: Role
    key: UUID


class PrivateInvitationDetail(InternalModel):
    id: int
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


class InvitationRespondentResponse(PublicModel):
    """This model is returned to the user on the invitation request
    for respondent roles.
    """

    secret_user_id: str
    nickname: str
    applet_id: int
    applet_name: str
    role: Role = Role.RESPONDENT
    key: UUID
    status: str


class InvitationManagersResponse(PublicModel):
    """This model is returned to the user on the invitation request
    for managers roles - "manager", "coordinator", "editor".
    """

    email: EmailStr
    applet_id: int
    applet_name: str
    role: ManagersRole
    key: UUID
    status: str


class PrivateInvitationResponse(PublicModel):
    applet_id: int
    applet_name: str
    role: Role
    key: UUID
    status: str
