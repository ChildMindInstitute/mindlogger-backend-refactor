import uuid

from apps.authentication.services import AuthenticationService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.errors import NotFoundError
from apps.users.crud import UsersCRUD
from apps.users.domain import (
    PasswordRecoveryApproveRequest,
    PasswordRecoveryInfo,
    PasswordRecoveryRequest,
    PublicUser,
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
    ) -> PublicUser:

        user: User = await UsersCRUD().get_by_email(schema.email)

        # If already exist password recovery for this user in Redis,
        # delete old password recovery, before generate and send new.
        await self._cache.delete_all_entries(email=schema.email)

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

        exp = settings.authentication.password_recover.expiration // 60

        html_payload: dict = {
            "email": user.email,
            "expiration_minutes": exp,
            "link": (
                f"{settings.service.urls.frontend.web_base}"
                f"/{settings.service.urls.frontend.password_recovery_send}"
                f"/{password_recovery_info.key}?email={user.email}"
            ),
        }
        message = MessageSchema(
            recipients=[user.email],
            subject="Password recovery for Mindlogger",
            body=service.get_template(
                path="password_recovery", **html_payload
            ),
        )
        await service.send(message)

        public_user = PublicUser(**user.dict())

        return public_user

    async def approve(
        self, schema: PasswordRecoveryApproveRequest
    ) -> PublicUser:
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

        public_user = PublicUser(**user.dict())

        # Delete cache entries
        await self._cache.delete_all_entries(email=schema.email)

        return public_user
