from fastapi.routing import APIRouter
from starlette import status

from apps.invitations.api import (
    invitation_approve,
    invitation_decline,
    invitation_list,
    invitation_retrieve,
    invitation_send,
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

# Invitation send
router.post(
    "/invite",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_send)

# Approve invitation
router.post(
    "/approve/{key}",
)(invitation_approve)

# Decline invitation
router.post(
    "/decline/{key}",
)(invitation_decline)

router.get(
    "/{key}",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_retrieve)
