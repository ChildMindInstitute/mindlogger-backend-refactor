import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.invitations.domain import (
    InvitationDetailForReviewer,
    InvitationManagersRequest,
    InvitationManagersResponse,
    InvitationRespondentRequest,
    InvitationRespondentResponse,
    InvitationResponse,
    InvitationReviewerRequest,
    InvitationReviewerResponse,
    PrivateInvitationResponse,
)
from apps.invitations.errors import InvitationDoesNotExist
from apps.invitations.services import (
    InvitationsService,
    PrivateInvitationService,
)
from apps.shared.domain import Response, ResponseMulti
from apps.users.domain import User
from infrastructure.database import atomic, session_manager


async def invitation_list(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations for the specific user who is invitor."""
    async with atomic(session):
        invitations = await InvitationsService(session, user).fetch_all()

    return ResponseMulti[InvitationResponse](
        result=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ]
    )


async def invitation_list_for_invited(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations for the specific user who is invited."""
    async with atomic(session):
        invitations = await InvitationsService(
            session, user
        ).fetch_all_for_invited()

    return ResponseMulti[InvitationResponse](
        result=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ]
    )


async def invitation_retrieve(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[InvitationResponse]:
    """Get specific invitation with approve key for user
    who was invited.
    """
    async with atomic(session):
        invitation = await InvitationsService(session, user).get(key)
        if not invitation:
            raise InvitationDoesNotExist(
                message=f"No such invitation with key={key}."
            )
    return Response(result=InvitationResponse.from_orm(invitation))


async def private_invitation_retrieve(
    key: uuid.UUID,
    session=Depends(session_manager.get_session),
) -> Response[PrivateInvitationResponse]:
    async with atomic(session):
        invitation = await PrivateInvitationService(session).get_invitation(
            key
        )
    return Response(result=PrivateInvitationResponse.from_orm(invitation))


async def invitation_respondent_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationRespondentRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[InvitationRespondentResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a roles "respondent".
    """
    # Send the invitation using the internal Invitation service
    async with atomic(session):
        invitation = await InvitationsService(
            session, user
        ).send_respondent_invitation(applet_id, invitation_schema)

    return Response[InvitationRespondentResponse](
        result=InvitationRespondentResponse(**invitation.dict())
    )


async def invitation_reviewer_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationReviewerRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[InvitationReviewerResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him role "reviewer" for specific respondents.
    """

    # Send the invitation using the internal Invitation service
    async with atomic(session):
        invitation: InvitationDetailForReviewer = await InvitationsService(
            session, user
        ).send_reviewer_invitation(applet_id, invitation_schema)

    return Response[InvitationReviewerResponse](
        result=InvitationReviewerResponse(**invitation.dict())
    )


async def invitation_managers_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationManagersRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[InvitationManagersResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a one of roles:
    "manager", "coordinator", "editor".
    """

    # Send the invitation using the internal Invitation service
    async with atomic(session):
        invitation = await InvitationsService(
            session, user
        ).send_managers_invitation(applet_id, invitation_schema)

    return Response[InvitationManagersResponse](
        result=InvitationManagersResponse(**invitation.dict())
    )


async def invitation_accept(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """General endpoint to approve the applet invitation."""
    async with atomic(session):
        await InvitationsService(session, user).accept(key)


async def private_invitation_accept(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await PrivateInvitationService(session).accept_invitation(user.id, key)


async def invitation_decline(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """General endpoint to decline the applet invitation."""
    async with atomic(session):
        await InvitationsService(session, user).decline(key)
