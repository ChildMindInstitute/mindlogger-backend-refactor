import uuid

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import (
    Applet,
    UserAppletAccess,
    UserAppletAccessCreate,
)
from apps.invitations.domain import (
    INVITE_USER_TEMPLATE,
    Invitation,
    InvitationRequest,
    InviteApproveResponse,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.errors import NotFoundError
from apps.users.domain import User
from config import settings
from infrastructure.cache import BaseCacheService
from infrastructure.cache.domain import CacheEntry
from infrastructure.cache.errors import CacheNotFound


class InvitationsCache(BaseCacheService[Invitation]):
    async def get(self, email: str) -> CacheEntry[Invitation]:
        cache_entry: dict = await self._get(email)
        return CacheEntry[Invitation](**cache_entry)


class InvitationsService:
    def __init__(self, user: User) -> None:
        self._user: User = user

    async def send_invitation(self, schema: InvitationRequest) -> Invitation:
        # Create internal Invitation object
        invitation = Invitation(
            email=schema.email,
            applet_id=schema.applet_id,
            role=schema.role,
            # Generate random uuid base on recepient's email salt
            key=uuid.uuid3(uuid.uuid4(), schema.email),
            invitor_id=self._user.id,
        )

        # Save invitation to the cache
        _: CacheEntry[Invitation] = await InvitationsCache().set(
            key=invitation.email, instance=invitation
        )

        # Send email to the user
        service: MailingService = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject="Invitation to the FCM",
            body=INVITE_USER_TEMPLATE.format(
                applet=invitation.applet_id,
                role=invitation.role,
                link=(
                    f"{settings.service.urls.frontend.base}"
                    f"/{settings.service.urls.frontend.invitation_send}"
                ),
            ),
        )
        await service.send(message)

        return invitation

    async def approve(self, key: uuid.UUID) -> InviteApproveResponse:
        # TODO: Remove record from the cache after approval.
        # TODO: Discuss how to store the data in the cache to handle
        #       a lot of invitations for different applets

        error: Exception = NotFoundError("No invitations found.")

        try:
            cache_entry: CacheEntry[Invitation] = await InvitationsCache().get(
                self._user.email
            )
        except CacheNotFound:
            raise error

        # Validate the requested invitaiton key
        if cache_entry.instance.key != key:
            raise error

        # Get applet from the database
        applet: Applet = await AppletsCRUD().get_by_id(
            cache_entry.instance.applet_id
        )

        # Create a user_applet_access record
        user_applet_access_create_schema = UserAppletAccessCreate(
            user_id=self._user.id,
            applet_id=cache_entry.instance.applet_id,
            role=cache_entry.instance.role,
        )
        user_applet_access: UserAppletAccess = (
            await UserAppletAccessCRUD().save(user_applet_access_create_schema)
        )

        return InviteApproveResponse(
            applet=applet, role=user_applet_access.role
        )
