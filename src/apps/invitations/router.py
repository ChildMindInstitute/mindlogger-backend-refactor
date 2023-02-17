from fastapi.routing import APIRouter
from starlette import status

from apps.invitations.api import (
    invitation_accept,
    invitation_decline,
    invitation_list,
    invitation_retrieve,
    invitation_send,
    private_invitation_accept,
    private_invitation_retrieve,
)
from apps.invitations.domain import InvitationResponse
from apps.shared.domain.response import (
    DEFAULT_OPENAPI_RESPONSE,
    Response,
    ResponseMulti,
)

router = APIRouter(prefix="/invitations", tags=["Invitations"])

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
    "/{key}/accept",
)(invitation_accept)

# Decline invitation
router.post(
    "/{key}/decline",
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

router.get(
    "/private/{key}",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(private_invitation_retrieve)
router.post("/private/{key}/accept")(private_invitation_accept)
