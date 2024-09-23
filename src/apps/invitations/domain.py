import uuid
from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Extra, Field, root_validator, validator

from apps.applets.domain import ManagersRole, Role
from apps.invitations.constants import InvitationStatus
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.domain.custom_validations import lowercase, lowercase_email


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
    language: InvitationLanguage = Field(description="This field represents the language of invitation")

    @root_validator
    def email_validation(cls, values):
        return lowercase_email(values)


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
    tag: str | None = Field(description="This field represents the tag/label of invited user")


class InvitationReviewerRequest(_InvitationRequest):
    """This model is used to send the invitation request
    to the user for "reviewer" role.
    """

    subjects: list[uuid.UUID] = Field(
        description="This field represents the list of subject id's",
    )
    workspace_prefix: str | None = Field(
        description="This field represents the user workspace prefix. "
        "You can only set this field the first time you invite any "
        "manager role to your applet. Once created, "
        "this name can not be changed anymore.",
        default=None,
    )
    title: str | None = Field(description="This field represents the team member title")


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

    title: str | None = Field(description="This field represents the team member title")


class RespondentMeta(InternalModel):
    """This model is used for internal needs
    for representation respondent meta information.
    """

    subject_id: str | None
    # This attribute has been moved to the 'subject' table and left here for backwards compatibility.
    # There is no need to use it for its intended purpose.
    secret_user_id: str | None


class RespondentInfo(InternalModel):
    nickname: str | None
    meta: RespondentMeta


class ReviewerMeta(InternalModel):
    """This model is used for internal needs
    for representation reviewer meta information.
    """

    class Config:
        extra = Extra.ignore

    subjects: list[str]


class _Invitation(InternalModel):
    id: uuid.UUID
    email: EmailStr
    applet_id: uuid.UUID
    role: Role
    key: uuid.UUID
    status: str
    invitor_id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None
    is_deleted: bool
    tag: str | None
    title: str | None


class Invitation(_Invitation):
    """This is an invitation representation for internal needs."""

    first_name: str
    last_name: str


class InvitationRespondent(_Invitation):
    """This is an invitation representation for internal needs."""

    meta: RespondentMeta
    nickname: str | None


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
    user_id: uuid.UUID | None
    tag: str | None
    title: str | None


class InvitationDetail(InvitationDetailBase):
    """This is an invitation representation for to get
    invitations from the database for other roles
    """

    meta: dict
    nickname: str | None
    secret_user_id: str | None


class InvitationDetailRespondent(InvitationDetailBase):
    """This is an invitation representation for to get
    invitations from the database for respondent roles
    """

    meta: RespondentMeta
    nickname: str | None
    secret_user_id: str


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
    first_name: str
    last_name: str
    user_id: uuid.UUID | None
    tag: str | None


class InvitationDetailForRespondent(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for respondent.
    """

    secret_user_id: str
    nickname: str | None
    role: Role = Role.RESPONDENT


class InvitationDetailForReviewer(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for reviewer.
    """

    email: EmailStr
    role: Role = Role.REVIEWER
    subjects: list[uuid.UUID]
    title: str | None


class InvitationDetailForManagers(_InvitationDetail):
    """This model is used for internal needs,
    as representation invitation detail for managers.
    """

    email: EmailStr
    role: ManagersRole
    title: str | None


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
    nickname: str | None
    secret_user_id: str | None
    tag: str | None
    title: str | None


class _InvitationResponse(PublicModel):
    """This model is used as base class for invitation response."""

    id: uuid.UUID = Field(
        description="This field represents the specific invitation id",
    )
    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id " "for invitation",
    )
    applet_name: str = Field(
        description="This field represents the specific applet name " "for invitation",
    )
    key: uuid.UUID = Field(
        description="This field represents the universally unique " "identifiers for invitation",
    )
    status: InvitationStatus = Field(
        description="This field represents the status for invitation",
    )
    first_name: str = Field(
        description="This field represents the first name of invited user",
    )
    last_name: str = Field(
        description="This field represents the last name of invited user",
    )
    user_id: uuid.UUID | None = Field(
        None,
        description="This field respresents registered user or not. " "Used for tests",
    )
    tag: str | None = Field(None, description="This field represents subject tag")


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

    email: EmailStr = Field(
        description="This field represents the email of invited reviewer",
    )
    subjects: list[uuid.UUID] = Field(description="This field represents the list of subject id's")
    role: Role = Role.REVIEWER
    title: str | None = Field(description="This field represents the team member title")


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
    title: str | None = Field(description="This field represents the team member title")


class PrivateInvitationResponse(PublicModel):
    applet_id: uuid.UUID
    applet_name: str
    role: Role
    key: uuid.UUID
    status: str


InvitationDetailGeneric = InvitationDetailReviewer | InvitationDetailRespondent | InvitationDetail


class ShellAccountCreateRequest(PublicModel):
    language: str
    first_name: str
    last_name: str
    secret_user_id: str
    nickname: str | None
    email: str | None
    tag: str | None

    _email_lower = validator("email", pre=True, allow_reuse=True)(lowercase)


class ShellAccountInvitation(PublicModel):
    email: EmailStr = Field(description="This field represents the email of invited subject")
    subject_id: uuid.UUID = Field(description="This field represents the subject id")
    language: InvitationLanguage | None = Field(description="This field represents the language of invitation")

    _email_lower = validator("email", pre=True, allow_reuse=True)(lowercase)
