from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.invitations.domain import (
    Invitation,
    InvitationRequest,
    InvitationResponse,
)
from apps.invitations.services import InvitationsService
from apps.shared.domain import Response
from apps.users.domain import User


async def send_invitation(
    user: User = Depends(get_current_user),
    invitation_schema: InvitationRequest = Body(...),
) -> Response[InvitationResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a role.
    """

    # Send the invitation using the internal Invitation service
    invitation: Invitation = await InvitationsService(user).send_invitation(
        invitation_schema
    )

    return Response[InvitationResponse](
        result=InvitationResponse(**invitation.dict())
    )
