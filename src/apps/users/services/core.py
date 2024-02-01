import urllib.parse
import uuid

from apps.authentication.services import AuthenticationService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    PasswordRecoveryApproveRequest,
    PasswordRecoveryInfo,
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserChangePassword,
)
from apps.users.errors import PasswordRecoveryKeyNotFound
from apps.users.services import PasswordRecoveryCache
from config import settings
from infrastructure.cache import CacheNotFound
from infrastructure.cache.domain import CacheEntry

__all__ = ["PasswordRecoveryService"]


class PasswordRecoveryService:
    def __init__(self, session) -> None:
        self._cache: PasswordRecoveryCache = PasswordRecoveryCache()
        self.session = session

    async def fetch_all(self, email: str) -> list[PasswordRecoveryInfo]:
        cache_entries: list[
            CacheEntry[PasswordRecoveryInfo]
        ] = await self._cache.all(email=email)

        return [entry.instance for entry in cache_entries]

    async def send_password_recovery(
        self, schema: PasswordRecoveryRequest
    ) -> PublicUser:
        # encrypted_email = encrypt(bytes(schema.email, "utf-8")).hex()

        user: User = await UsersCRUD(self.session).get_by_email(schema.email)

        if user.email_encrypted != schema.email:
            user = await UsersCRUD(self.session).update_encrypted_email(
                user, schema.email
            )

        # If already exist password recovery for this user in Redis,
        # delete old password recovery, before generate and send new.
        await self._cache.delete_all_entries(
            email=user.email_encrypted  # type: ignore[arg-type]
        )

        password_recovery_info = PasswordRecoveryInfo(
            email=user.email_encrypted,
            user_id=user.id,
            key=uuid.uuid3(
                uuid.uuid4(), user.email_encrypted  # type: ignore[arg-type]
            ),
        )

        # Build the cache key
        key: str = self._cache.build_key(
            user.email_encrypted,  # type: ignore[arg-type]
            password_recovery_info.key,
        )

        # Save password recovery to the cache
        _: CacheEntry[PasswordRecoveryInfo] = await self._cache.set(
            key=key,
            instance=password_recovery_info,
            ttl=settings.authentication.password_recover.expiration,
        )

        # Send email to the user
        service = MailingService()

        exp = settings.authentication.password_recover.expiration // 60

        url = (
            f"https://{settings.service.urls.frontend.web_base}"
            f"/{settings.service.urls.frontend.password_recovery_send}"
            f"?key={password_recovery_info.key}"
            f"&email="
            f"{urllib.parse.quote(user.email_encrypted)}"  # type: ignore
        )

        message = MessageSchema(
            recipients=[user.email_encrypted],
            subject="Girder for MindLogger (development instance): "
            "Temporary access",
            body=service.get_template(
                path="reset_password_en",
                email=user.email_encrypted,
                expiration_minutes=exp,
                url=url,
            ),
        )
        await service.send(message)

        public_user = PublicUser.from_user(user)

        return public_user

    async def approve(
        self, schema: PasswordRecoveryApproveRequest
    ) -> PublicUser:
        try:
            cache_entry: CacheEntry[
                PasswordRecoveryInfo
            ] = await self._cache.get(schema.email, schema.key)
        except CacheNotFound:
            raise PasswordRecoveryKeyNotFound()

        # Get user from the database
        user: User = await UsersCRUD(self.session).get_by_email(
            cache_entry.instance.email
        )

        # Update password for user
        user_change_password_schema = UserChangePassword(
            hashed_password=AuthenticationService(
                self.session
            ).get_password_hash(schema.password)
        )
        user = await UsersCRUD(self.session).change_password(
            user, user_change_password_schema
        )

        public_user = PublicUser.from_user(user)

        # Delete cache entries
        await self._cache.delete_all_entries(email=schema.email)

        return public_user
