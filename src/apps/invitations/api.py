import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.invitations.domain import (
    InvitationDetail,
    InvitationDetailForManagers,
    InvitationDetailForRespondent,
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
from apps.invitations.filters import InvitationQueryParams
from apps.invitations.services import (
    InvitationsService,
    PrivateInvitationService,
)
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User


async def invitation_list(
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(InvitationQueryParams)
    ),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations whose status is pending
    for the specific user who is invitor.
    """

    invitations: list[InvitationDetail] = await InvitationsService(
        user
    ).fetch_all(deepcopy(query_params))

    count: int = await InvitationsService(user).fetch_all_count(
        deepcopy(query_params)
    )

    return ResponseMulti[InvitationResponse](
        result=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ],
        count=count,
    )


async def invitation_list_for_invited(
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(InvitationQueryParams)
    ),
) -> ResponseMulti[InvitationResponse]:
    """Fetch all invitations whose status is pending
    for the specific user who was invited.
    """

    invitations: list[InvitationDetail] = await InvitationsService(
        user
    ).fetch_all_for_invited(deepcopy(query_params))

    count: int = await InvitationsService(user).fetch_all_for_invited_count(
        deepcopy(query_params)
    )

    return ResponseMulti[InvitationResponse](
        result=[
            InvitationResponse(**invitation.dict())
            for invitation in invitations
        ],
        count=count,
    )


async def invitation_retrieve(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
) -> Response[InvitationResponse]:
    """Get specific invitation with approve key for user
    who was invited.
    """

    invitation = await InvitationsService(user).get(key)
    if not invitation:
        raise InvitationDoesNotExist(
            message=f"No such invitation with key={key}."
        )
    return Response(result=InvitationResponse.from_orm(invitation))


async def private_invitation_retrieve(
    key: uuid.UUID,
) -> Response[PrivateInvitationResponse]:
    invitation = await PrivateInvitationService().get_invitation(key)
    return Response(result=PrivateInvitationResponse.from_orm(invitation))


async def invitation_respondent_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationRespondentRequest = Body(...),
) -> Response[InvitationRespondentResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a roles "respondent".
    """

    # Send the invitation using the internal Invitation service
    invitation: InvitationDetailForRespondent = await InvitationsService(
        user
    ).send_respondent_invitation(applet_id, invitation_schema)

    return Response[InvitationRespondentResponse](
        result=InvitationRespondentResponse(**invitation.dict())
    )


async def invitation_reviewer_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationReviewerRequest = Body(...),
) -> Response[InvitationReviewerResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him role "reviewer" for specific respondents.
    """

    # Send the invitation using the internal Invitation service
    invitation: InvitationDetailForReviewer = await InvitationsService(
        user
    ).send_reviewer_invitation(applet_id, invitation_schema)

    return Response[InvitationReviewerResponse](
        result=InvitationReviewerResponse(**invitation.dict())
    )


async def invitation_managers_send(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    invitation_schema: InvitationManagersRequest = Body(...),
) -> Response[InvitationManagersResponse]:
    """General endpoint for sending invitations to the concrete applet
    for the concrete user giving him a one of roles:
    "manager", "coordinator", "editor".
    """

    # Send the invitation using the internal Invitation service
    invitation: InvitationDetailForManagers = await InvitationsService(
        user
    ).send_managers_invitation(applet_id, invitation_schema)

    return Response[InvitationManagersResponse](
        result=InvitationManagersResponse(**invitation.dict())
    )


async def invitation_accept(
    key: uuid.UUID, user: User = Depends(get_current_user)
):
    """General endpoint to approve the applet invitation."""
    await InvitationsService(user).accept(key)


async def private_invitation_accept(
    key: uuid.UUID,
    user: User = Depends(get_current_user),
):
    await PrivateInvitationService().accept_invitation(user.id, key)


async def invitation_decline(
    key: uuid.UUID, user: User = Depends(get_current_user)
):
    """General endpoint to decline the applet invitation."""
    await InvitationsService(user).decline(key)
