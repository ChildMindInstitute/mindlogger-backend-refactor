import uuid
from uuid import UUID

from fastapi import Body, Depends
from fastapi import Response as FastApiResponse
from fastapi import status

from apps.authentication.deps import get_current_user
from apps.invitations.domain import (
    InvitationDetail,
    InvitationRequest,
    InvitationResponse,
    PrivateInvitationResponse,
)
from apps.invitations.services import (
    InvitationsService,
    PrivateInvitationService,
)
from apps.shared.domain import Response, ResponseMulti
from apps.users.domain import User


async def invitation_list(
    user: User = Depends(get_current_user),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations for the specific user."""

    invitations: list[InvitationDetail] = await InvitationsService(
        user
    ).fetch_all()

    return ResponseMulti[InvitationResponse](
        result=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ]
    )


async def invitation_retrieve(
    key: str,
    response: FastApiResponse,
    user: User = Depends(get_current_user),
) -> Response[InvitationResponse]:
    invitation = await InvitationsService(user).get(key)
    if not invitation:
        response.status_code = status.HTTP_204_NO_CONTENT
        return Response(result=None)
    return Response(result=InvitationResponse.from_orm(invitation))


async def private_invitation_retrieve(
    key: uuid.UUID,
) -> Response[PrivateInvitationResponse]:
    invitation = await PrivateInvitationService().get_invitation(key)
    return Response(result=PrivateInvitationResponse.from_orm(invitation))


async def invitation_send(
    user: User = Depends(get_current_user),
    invitation_schema: InvitationRequest = Body(...),
) -> Response[InvitationResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a role.
    """

    # Send the invitation using the internal Invitation service
    invitation: InvitationDetail = await InvitationsService(
        user
    ).send_invitation(invitation_schema)

    return Response[InvitationResponse](
        result=InvitationResponse(**invitation.dict())
    )


async def invitation_accept(key: UUID, user: User = Depends(get_current_user)):
    """General endpoint to approve the applet invitation."""
    await InvitationsService(user).accept(key)


async def private_invitation_accept(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
):
    await PrivateInvitationService().accept_invitation(user.id, key)


async def invitation_decline(
    key: UUID, user: User = Depends(get_current_user)
):
    """General endpoint to decline the applet invitation."""
    await InvitationsService(user).decline(key)
