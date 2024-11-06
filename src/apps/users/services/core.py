import urllib.parse
import uuid
from typing import cast

from apps.authentication.services import AuthenticationService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.enums import Language
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
from infrastructure.http.domain import MindloggerContentSource

__all__ = ["PasswordRecoveryService"]


class PasswordRecoveryService:
    def __init__(self, session) -> None:
        self._cache: PasswordRecoveryCache = PasswordRecoveryCache()
        self.session = session

    async def send_password_recovery(
        self,
        schema: PasswordRecoveryRequest,
        content_source: MindloggerContentSource,
        language: Language,
    ) -> PublicUser:
        user: User = await UsersCRUD(self.session).get_by_email(schema.email)

        if user.email_encrypted != schema.email:
            user = await UsersCRUD(self.session).update_encrypted_email(user, schema.email)
        user.email_encrypted = cast(str, user.email_encrypted)

        # If already exist password recovery for this user in Redis,
        # delete old password recovery, before generate and send new.
        await self._cache.delete_all_entries(email=user.email_encrypted)

        password_recovery_info = PasswordRecoveryInfo(
            email=user.email_encrypted,
            user_id=user.id,
            key=uuid.uuid3(
                uuid.uuid4(),
                user.email_encrypted,
            ),
        )

        # Build the cache key
        key: str = self._cache.build_key(
            user.email_encrypted,
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

        # Default to web frontend
        frontend_base = settings.service.urls.frontend.web_base
        password_recovery_page = settings.service.urls.frontend.web_password_recovery_send

        if content_source == MindloggerContentSource.admin:
            # Change to admin frontend if the request came from there
            frontend_base = settings.service.urls.frontend.admin_base
            password_recovery_page = settings.service.urls.frontend.admin_password_recovery_send

        url = (
            f"https://{frontend_base}"
            f"/{password_recovery_page}"
            f"?key={password_recovery_info.key}"
            f"&email="
            f"{urllib.parse.quote(user.email_encrypted)}"
        )

        message = MessageSchema(
            recipients=[user.email_encrypted],
            subject="Password reset",
            subject=service.get_localized_string(
                key="password_reset_subject",
                language=language,
            ),
            body=service.get_localized_html_template(
                template_name="reset_password",
                language=language,
                email=user.email_encrypted,
                expiration_minutes=exp,
                url=url,
            ),
        )
        await service.send(message)

        public_user = PublicUser.from_user(user)

        return public_user

    async def approve(self, schema: PasswordRecoveryApproveRequest) -> PublicUser:
        try:
            cache_entry: CacheEntry[PasswordRecoveryInfo] = await self._cache.get(schema.email, schema.key)
        except CacheNotFound:
            raise PasswordRecoveryKeyNotFound()

        # Get user from the database
        user: User = await UsersCRUD(self.session).get_by_email(cache_entry.instance.email)

        # Update password for user
        user_change_password_schema = UserChangePassword(
            hashed_password=AuthenticationService(self.session).get_password_hash(schema.password)
        )
        user = await UsersCRUD(self.session).change_password(user, user_change_password_schema)

        public_user = PublicUser.from_user(user)

        # Delete cache entries
        await self._cache.delete_all_entries(email=schema.email)

        return public_user
