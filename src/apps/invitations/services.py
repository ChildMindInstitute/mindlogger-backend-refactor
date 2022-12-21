import json
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
    """The concrete class that realized invitations cache engine.
    In order to be able to save multiple invitations for a single user
    the specific key builder is used.

    The example of a key:
        __classname__:john@email.com:fe46c05a-1790-4bea-8066-5e2572b4b413

    __classname__ -- is taken from the parent class key builder
    john@email.com -- user's email
    fe46c05a-1790-4bea-8066-5e2572b4b413 -- invitaiton UUID

    This strategy is taken in order to create unique pairs
    that consist of user's email and unique invitation's identifier
    """

    def build_key(self, email: str, key: uuid.UUID | str) -> str:
        """Returns a key with the additional namespace for this cache."""

        return f"{email}:{key}"

    async def get(
        self, email: str, key: uuid.UUID | str
    ) -> CacheEntry[Invitation]:
        cache_record: dict = await self._get(self.build_key(email, key))

        return CacheEntry[Invitation](**cache_record)

    async def delete(self, email: str, key: uuid.UUID | str) -> None:
        _key = self.build_key(email, key)
        await self._delete(_key)

    async def all(self, email: str) -> list[CacheEntry[Invitation]]:
        # Create a key to fetch all records for
        # the specific email prefix in a cache key
        key = f"{email}:*"

        # Fetch keys for retrieving
        if not (keys := await self.redis_client.keys(self._build_key(key))):
            raise CacheNotFound(f"There is no invitations for {email}")

        results: list[bytes] = await self.redis_client.mget(keys)

        return [
            CacheEntry[Invitation](**json.loads(result)) for result in results
        ]


class InvitationsService:
    def __init__(self, user: User) -> None:
        self._user: User = user
        self._cache = InvitationsCache()

    async def fetch_all(self) -> list[Invitation]:
        cache_entries: list[CacheEntry[Invitation]] = await self._cache.all(
            email=self._user.email
        )

        return [entry.instance for entry in cache_entries]

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

        # Build the cache key that consis of user's email and applet's id
        key: str = self._cache.build_key(invitation.email, invitation.key)

        # Save invitation to the cache
        _: CacheEntry[Invitation] = await self._cache.set(
            key=key, instance=invitation
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
            cache_entry: CacheEntry[Invitation] = await self._cache.get(
                self._user.email, key
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

        # Delete cache entry
        await self._cache.delete(email=self._user.email, key=key)

        return InviteApproveResponse(
            applet=applet, role=user_applet_access.role
        )
