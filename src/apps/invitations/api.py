from uuid import UUID

from fastapi import Body, Depends

from apps.applets.crud import AppletsCRUD
from apps.authentication.deps import get_current_user
from apps.invitations.domain import (
    Invitation,
    InvitationRequest,
    InvitationResponse,
    InviteApproveResponse,
)
from apps.invitations.services import InvitationsService
from apps.shared.domain import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


async def invitations(
    user: User = Depends(get_current_user),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations for the specific user."""

    invitations: list[Invitation] = await InvitationsService(user).fetch_all()

    return ResponseMulti[InvitationResponse](
        results=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ]
    )


async def send_invitation(
    user: User = Depends(get_current_user),
    invitation_schema: InvitationRequest = Body(...),
) -> Response[InvitationResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a role.
    """

    # TODO: Replace with `await BaseCRUD().exists()`
    # Check if applet exists in the database
    await AppletsCRUD().get_by_id(invitation_schema.applet_id)

    # Send the invitation using the internal Invitation service
    invitation: Invitation = await InvitationsService(user).send_invitation(
        invitation_schema
    )

    return Response[InvitationResponse](
        result=InvitationResponse(**invitation.dict())
    )


async def approve_invite(
    key: UUID, user: User = Depends(get_current_user)
) -> Response[InviteApproveResponse]:
    """General endpoint to approve the applet invitation."""

    # Approve the invitaiton for the specific applet
    # if data exists tokens are not expired
    result: InviteApproveResponse = await InvitationsService(user).approve(key)

    return Response[InviteApproveResponse](result=result)


async def decline_invite(
    key: UUID, user: User = Depends(get_current_user)
) -> Response[InviteApproveResponse]:
    """General endpoint to declnie the applet invitation."""

    await InvitationsService(user).decline(key)

    raise NotContentError
