from fastapi.routing import APIRouter
from starlette import status

from apps.invitations.api import (
    invitation_accept,
    invitation_decline,
    invitation_list,
    invitation_managers_send,
    invitation_respondent_send,
    invitation_retrieve,
    invitation_reviewer_send,
    invitation_send,
    private_invitation_accept,
    private_invitation_retrieve,
)
from apps.invitations.domain import (
    InvitationManagersResponse,
    InvitationRespondentResponse,
    InvitationResponse,
    InvitationReviewerResponse,
    PrivateInvitationResponse,
)
from apps.shared.domain.response import (
    DEFAULT_OPENAPI_RESPONSE,
    Response,
    ResponseMulti,
)

router = APIRouter(prefix="/applets", tags=["Invitations"])

# Invitations list
router.get(
    "",
    response_model=ResponseMulti[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_list)

router.get(
    "/{key}",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_retrieve)

# Approve invitation
router.post(
    "/{key}/invitations/approve",
)(invitation_accept)

# Decline invitation
router.delete(
    "/{key}/invitations/decline",
)(invitation_decline)

# Invitation send
router.post(
    "/invite",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_send)

# Invitation send for Role respondent
router.post(
    "/{applet_id}/invitations/respondent",
    response_model=Response[InvitationRespondentResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationRespondentResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_respondent_send)

# Invitation send for Role reviewer
router.post(
    "/{applet_id}/invitations/reviewer",
    response_model=Response[InvitationReviewerResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationReviewerResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_reviewer_send)

# Invitation send for other Role ("manager", "coordinator", "editor")
router.post(
    "/{applet_id}/invitations/managers",
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
