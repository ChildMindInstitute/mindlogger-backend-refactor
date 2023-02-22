import uuid
from uuid import UUID

from pydantic import EmailStr, Field

from apps.applets.domain import ManagersRole, Role
from apps.invitations.constants import InvitationStatus
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


class _InvitationRequest(PublicModel):
    """This model is used as base class for invitation requests."""

    email: EmailStr = Field(
        description="This field represents the email of invited user",
    )
    first_name: str = Field(
        description="This field represents the first name of invited user",
    )
    last_name: str = Field(
        description="This field represents the last name of invited user",
    )
    language: str = Field(
        description="This field represents the language of invitation",
        max_length=2,
    )


class InvitationRespondentRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for the respondent roles.
    """

    secret_user_id: str = Field(
        description="This field represents the secret user id "
        "which is intended to preserve the confidentiality "
        "of the respondent, this user identifier is unique "
        "within the applet",
    )
    nickname: str = Field(
        description="This field represents the nickname of respondent, "
        "this is the identifier that is assigned by the applet manager "
        "when the respondent is invited, it is intended to increase "
        "representativeness but preserve confidentiality",
    )


class InvitationReviewerRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for "reviewer" role.
    """

    respondents: list[int] = Field(
        description="This field represents the list of users id's "
        "which invited to the applet as a respondents",
    )


class InvitationManagersRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for managers roles - "manager", "coordinator", "editor".
    """

    role: ManagersRole = Field(
        description="This field represents the managers role",
    )


class Invitation(InternalModel):
    """This is an invitation representation for internal needs."""

    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    role: Role
    key: UUID
    status: str
    invitor_id: int


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


class _InvitationDetail(InternalModel):
    """This model is used for internal needs,
    as base class for invitation detail.
    """

    id: int
    applet_id: int
    applet_name: str
    status: str
    key: UUID


class InvitationDetailForRespondent(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for respondent.
    """

    secret_user_id: str
    nickname: str
    role: Role = Role.RESPONDENT


class InvitationDetailForReviewer(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for reviewer.
    """

    email: EmailStr
    role: Role = Role.REVIEWER
    respondents: list[int]


class InvitationDetailForManagers(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for managers.
    """

    email: EmailStr
    role: ManagersRole


class PrivateInvitationDetail(InternalModel):
    id: uuid.UUID
    applet_id: uuid.UUID
    status: str
    applet_name: str
    role: Role
    key: UUID


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


class _InvitationResponse(PublicModel):
    """This model is used as base class for invitation response."""

    applet_id: int = Field(
        description="This field represents the specific applet id "
        "for invitation",
    )
    applet_name: str = Field(
        description="This field represents the specific applet name "
        "for invitation",
    )
    key: UUID = Field(
        description="This field represents the universally unique "
        "identifiers for invitation",
    )
    status: InvitationStatus = Field(
        description="This field represents the status for invitation",
    )


class InvitationRespondentResponse(_InvitationResponse):
    """This model is returned to the user on the invitation response
    for respondent role.
    """

    secret_user_id: str = Field(
        description="This field represents the secret user id "
        "which is intended to preserve the confidentiality "
        "of the respondent, this user identifier is unique "
        "within the applet",
    )
    nickname: str = Field(
        description="This field represents the nickname of respondent, "
        "this is the identifier that is assigned by the applet manager "
        "when the respondent is invited, it is intended to increase "
        "representativeness but preserve confidentiality",
    )
    role: Role = Role.RESPONDENT


class InvitationReviewerResponse(_InvitationResponse):
    """This model is returned to the user on the invitation response
    for reviewer role.
    """

    respondents: list[int] = Field(
        description="This field represents the list of users id's "
        "which invited to the applet as a respondents",
    )
    role: Role = Role.REVIEWER


class InvitationManagersResponse(_InvitationResponse):
    """This model is returned to the user on the invitation response
    for managers roles - "manager", "coordinator", "editor".
    """

    email: EmailStr = Field(
        description="This field represents the email of invited manager",
    )
    role: ManagersRole = Field(
        description="This field represents the managers role",
    )


class PrivateInvitationResponse(PublicModel):
    applet_id: uuid.UUID
    applet_name: str
    role: Role
    key: UUID
    status: str
