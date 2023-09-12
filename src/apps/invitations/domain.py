import uuid
from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Field

from apps.applets.domain import ManagersRole, Role
from apps.invitations.constants import InvitationStatus
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.encryption import encrypt


class Applet(PublicModel):
    id: uuid.UUID
    display_name: str


class InvitationLanguage(str, Enum):
    EN = "en"
    FR = "fr"


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
    language: InvitationLanguage = Field(
        description="This field represents the language of invitation"
    )

    @property
    def encrypted_first_name(self) -> str | None:
        if self.first_name:
            return encrypt(bytes(self.first_name, "utf-8")).hex()
        return None

    @property
    def encrypted_last_name(self) -> str | None:
        if self.last_name:
            return encrypt(bytes(self.last_name, "utf-8")).hex()
        return None


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
    nickname: str | None = Field(
        description="This field represents the nickname of respondent, "
        "this is the identifier that is assigned by the applet manager "
        "when the respondent is invited, it is intended to increase "
        "representativeness but preserve confidentiality",
        default_factory=str,
    )


class InvitationReviewerRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for "reviewer" role.
    """

    respondents: list[uuid.UUID] = Field(
        description="This field represents the list of users id's "
        "which invited to the applet as a respondents",
    )
    workspace_prefix: str | None = Field(
        description="This field represents the user workspace prefix. "
        "You can only set this field the first time you invite any "
        "manager role to your applet. Once created, "
        "this name can not be changed anymore.",
        default=None,
    )

    @property
    def encrypted_workspace_prefix(self) -> str | None:
        if self.workspace_prefix:
            return encrypt(bytes(self.workspace_prefix, "utf-8")).hex()
        return None


class InvitationManagersRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for managers roles - "manager", "coordinator", "editor".
    """

    role: ManagersRole = Field(
        description="This field represents the managers role",
    )
    workspace_prefix: str | None = Field(
        description="This field represents the user workspace prefix. "
        "You can only set this field the first time you invite any "
        "manager role to your applet. Once created, "
        "this name can not be changed anymore.",
        default=None,
    )

    @property
    def encrypted_workspace_prefix(self) -> str | None:
        if self.workspace_prefix:
            return encrypt(bytes(self.workspace_prefix, "utf-8")).hex()
        return None


class RespondentMeta(InternalModel):
    """This model is used for internal needs
    for representation respondent meta information.
    """

    secret_user_id: str
    nickname: str


class ReviewerMeta(InternalModel):
    """This model is used for internal needs
    for representation reviewer meta information.
    """

    respondents: list[str]


class Invitation(InternalModel):
    """This is an invitation representation for internal needs."""

    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    role: Role
    key: uuid.UUID
    status: str
    invitor_id: uuid.UUID
    first_name: str
    last_name: str
    created_at: datetime


class InvitationRespondent(Invitation):
    """This is an invitation representation for internal needs."""

    meta: RespondentMeta


class InvitationReviewer(Invitation):
    """This is an invitation representation for internal needs."""

    meta: ReviewerMeta


class InvitationManagers(Invitation):
    """This is an invitation representation for internal needs."""

    meta: dict


class InvitationDetailBase(InternalModel):
    """This is an invitation representation for internal needs."""

    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    status: str
    applet_name: str
    invitor_id: uuid.UUID
    role: Role
    key: uuid.UUID
    first_name: str
    last_name: str
    created_at: datetime


class InvitationDetail(InvitationDetailBase):
    """This is an invitation representation for to get
    invitations from the database for other roles
    """

    meta: dict


class InvitationDetailRespondent(InvitationDetailBase):
    """This is an invitation representation for to get
    invitations from the database for respondent roles
    """

    meta: RespondentMeta


class InvitationDetailReviewer(InvitationDetailBase):
    """This is an invitation representation for to get
    invitations from the database for reviewer roles
    """

    meta: ReviewerMeta


class _InvitationDetail(InternalModel):
    """This model is used for internal needs,
    as base class for invitation detail.
    """

    id: uuid.UUID
    applet_id: uuid.UUID
    applet_name: str
    status: str
    key: uuid.UUID


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
    respondents: list[uuid.UUID]


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
    key: uuid.UUID


class InvitationResponse(PublicModel):
    """This model is returned to the user on the invitation request."""

    email: EmailStr
    applet_id: uuid.UUID
    applet_name: str
    role: Role
    key: uuid.UUID
    status: str
    first_name: str
    last_name: str
    created_at: datetime
    meta: dict


class _InvitationResponse(PublicModel):
    """This model is used as base class for invitation response."""

    id: uuid.UUID = Field(
        description="This field represents the specific invitation id",
    )
    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id "
        "for invitation",
    )
    applet_name: str = Field(
        description="This field represents the specific applet name "
        "for invitation",
    )
    key: uuid.UUID = Field(
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
    nickname: str | None = Field(
        default=None,
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

    respondents: list[uuid.UUID] = Field(
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
    key: uuid.UUID
    status: str


InvitationDetailGeneric = (
    InvitationDetailReviewer | InvitationDetailRespondent | InvitationDetail
)
