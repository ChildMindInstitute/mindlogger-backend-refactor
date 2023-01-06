import uuid

from apps.authentication.services import AuthenticationService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.errors import NotFoundError
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    PASSWORD_RECOVERY_TEMPLATE,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryInfo,
    PasswordRecoveryRequest,
    User,
    UserChangePassword,
)
from apps.users.services import PasswordRecoveryCache
from config import settings
from infrastructure.cache import CacheNotFound
from infrastructure.cache.domain import CacheEntry

__all__ = ["PasswordRecoveryService"]


class PasswordRecoveryService:
    def __init__(self) -> None:
        self._cache: PasswordRecoveryCache = PasswordRecoveryCache()

    async def fetch_all(self, email: str) -> list[PasswordRecoveryInfo]:
        cache_entries: list[
            CacheEntry[PasswordRecoveryInfo]
        ] = await self._cache.all(email=email)

        return [entry.instance for entry in cache_entries]
    
    async def send_password_recovery(
        self, schema: PasswordRecoveryRequest
    ) -> PasswordRecoveryInfo:

        user: User = await UsersCRUD().get_by_email(schema.email)

        # If already exist password recovery for this user in Redis,
        # delete old password recovery, before generate and send new.
        await self._cache.delete(email=user.email)

        password_recovery_info = PasswordRecoveryInfo(
            email=user.email,
            user_id=user.id,
            key=uuid.uuid3(uuid.uuid4(), user.email),
        )

        # Build the cache key
        key: str = self._cache.build_key(
            user.email, password_recovery_info.key
        )

        # Save password recovery to the cache
        _: CacheEntry[PasswordRecoveryInfo] = await self._cache.set(
            key=key,
            instance=password_recovery_info,
            ttl=settings.authentication.password_recover.expiration,
        )

        # Send email to the user
        service: MailingService = MailingService()
        message = MessageSchema(
            recipients=[user.email],
            subject="Password recovery for Mindlogger",
            body=PASSWORD_RECOVERY_TEMPLATE.format(
                link=(
                    f"{settings.service.urls.frontend.base}"
                    f"/{settings.service.urls.frontend.password_recovery_send}"
                ),
            ),
        )
        await service.send(message)

        return password_recovery_info

    async def approve(self, schema: PasswordRecoveryApproveRequest) -> User:
        error: Exception = NotFoundError("Password recovery key not found")

        try:
            cache_entry: CacheEntry[
                PasswordRecoveryInfo
            ] = await self._cache.get(schema.email, schema.key)
        except CacheNotFound:
            raise error

        # Get user from the database
        user: User = await UsersCRUD().get_by_email(cache_entry.instance.email)

        # Update password for user
        user_change_password_schema = UserChangePassword(
            hashed_password=AuthenticationService().get_password_hash(
                schema.password
            )
        )
        user = await UsersCRUD().change_password(
            user, user_change_password_schema
        )

        # Delete cache entry
        await self._cache.delete(email=user.email)

        return user
