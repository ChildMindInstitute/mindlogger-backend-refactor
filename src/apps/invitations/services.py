import uuid

from apps.invitations.domain import (
    INVITE_USER_TEMPLATE,
    Invitation,
    InvitationRequest,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.users.domain import User
from config import settings
from infrastructure.cache import BaseCacheService
from infrastructure.cache.domain import CacheEntry
from infrastructure.cache.errors import CacheNotFound


class InvitationsCache(BaseCacheService[Invitation]):
    async def get(self, email: str) -> CacheEntry[Invitation]:
        """Returns rich cache entry by email."""

        if cache_entry := await self.redis_client.get(
            name=self._get_key(key=email)
        ):
            return CacheEntry[Invitation].parse_obj(cache_entry)

        raise CacheNotFound(email)


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
