from uuid import UUID

from pydantic import EmailStr

from apps.applets.domain import Role
from apps.shared.domain import InternalModel, PublicModel


class InvitationRequest(InternalModel):
    """This model is used to send the invitation request
    to the user for the specific role.
    """

    email: EmailStr
    applet_id: int
    role: Role = Role.RESPONDENT


class Invitation(InternalModel):
    """This is an invitation representation for internal needs."""

    email: EmailStr
    applet_id: int
    role: Role
    key: UUID
    invitor_id: int


class InvitationResponse(PublicModel):
    """This model will be returned to the user on the invitation request."""

    email: EmailStr
    applet_id: int
    role: Role
    key: UUID


INVITE_USER_TEMPLATE = """
You was invited to the Mindlogger to manage the applet {applet}.
Your role is {role}
Please follow the link: {link}
"""
