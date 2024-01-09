from fastapi.routing import APIRouter
from starlette import status

from apps.invitations.api import (
    create_shell_account,
    invitation_accept,
    invitation_decline,
    invitation_list,
    invitation_managers_send,
    invitation_respondent_send,
    invitation_retrieve,
    invitation_reviewer_send,
    private_invitation_accept,
    private_invitation_retrieve,
)
from apps.invitations.domain import (
    InvitationManagersResponse,
    InvitationRespondentResponse,
    InvitationResponse,
    InvitationReviewerResponse,
    PrivateInvitationResponse,
    ShellAccountCreateResponse,
)
from apps.shared.domain.response import (
    DEFAULT_OPENAPI_RESPONSE,
    Response,
    ResponseMulti,
)

router = APIRouter(prefix="/invitations", tags=["Invitations"])

# Invitations list
router.get(
    "",
    description="""Fetch all invitations whose status is pending
                for the specific user who is invitor.""",
    response_model_by_alias=True,
    response_model=ResponseMulti[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_list)


router.get(
    "/{key}",
    description="""Get specific invitation with approve key for user
                who was invited.""",
    response_model_by_alias=True,
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_retrieve)

# Accept invitation
router.post(
    "/{key}/accept",
)(invitation_accept)

# Decline invitation
router.delete(
    "/{key}/decline",
)(invitation_decline)


# Invitation send for Role respondent
router.post(
    "/{applet_id}/respondent",
    description="""General endpoint for sending invitations to the concrete
                applet for the concrete user giving him a roles
                "respondent".""",
    response_model_by_alias=True,
    response_model=Response[InvitationRespondentResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationRespondentResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_respondent_send)

# Invitation send for Role reviewer
router.post(
    "/{applet_id}/reviewer",
    description="""General endpoint for sending invitations to the concrete
                applet for the concrete user giving him role "reviewer"
                for specific respondents.""",
    response_model_by_alias=True,
    response_model=Response[InvitationReviewerResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationReviewerResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_reviewer_send)

# Invitation send for other Role ("manager", "coordinator", "editor")
router.post(
    "/{applet_id}/managers",
    description="""General endpoint for sending invitations to the concrete
    applet for the concrete user giving him a one of roles:
    "manager", "coordinator", "editor".""",
    response_model_by_alias=True,
    response_model=Response[InvitationManagersResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationManagersResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_managers_send)

router.get(
    "/private/{key}",
    response_model=Response[PrivateInvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[PrivateInvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(private_invitation_retrieve)

router.post("/private/{key}/accept")(private_invitation_accept)


# Invitation send for shell account
router.post(
    "/{applet_id}/shell-account",
    description="""
    Creation of shell account for current applet
    """,
    response_model_by_alias=True,
    response_model=Response[ShellAccountCreateResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[ShellAccountCreateResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(create_shell_account)
