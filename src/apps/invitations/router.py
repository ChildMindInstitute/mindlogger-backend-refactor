from fastapi.routing import APIRouter
from starlette import status

from apps.invitations.api import (
    invitation_approve,
    invitation_decline,
    invitation_list,
    invitation_retrieve,
    invitation_send,
)
from apps.invitations.domain import InvitationResponse, InviteApproveResponse
from apps.shared.domain.response import (
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
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
router.get(
    "/approve/{key}",
    response_model=Response[InviteApproveResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InviteApproveResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_approve)

# Decline invitation
router.delete(
    "/decline/{key}",
    response_model=None,
    responses={
        status.HTTP_200_OK: {},
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_decline)

router.get(
    "/{key}",
    response_model=Response[InvitationResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[InvitationResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(invitation_retrieve)
