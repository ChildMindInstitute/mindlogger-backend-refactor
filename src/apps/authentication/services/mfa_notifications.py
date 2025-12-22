"""MFA email notification service.

Handles email notifications for MFA security events:
- CRITICAL: Account lockout, last recovery code, MFA disabled
- HIGH: MFA enabled, recovery code used, failed attempts
- MEDIUM: Recovery codes viewed/downloaded
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from apps.authentication.services.mfa_helpers import (
    get_user_display_name,
    get_user_email,
    get_user_language,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.users.domain import User
from config import settings
from infrastructure.logger import logger


class MFANotificationService:
    """Sends MFA-related email notifications."""

    def __init__(self):
        self.mailing_service = MailingService()

    async def send_account_locked_email(
        self,
        user: User,
        lockout_reason: str,
        failed_attempts: int,
        lockout_ttl_seconds: Optional[int] = None,
    ) -> None:
        """Send email when account is locked after too many failed MFA attempts."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping account locked email user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            # Calculate lockout expiration time
            lockout_until = None
            if lockout_ttl_seconds:
                lockout_until = datetime.now(timezone.utc)
                # Add TTL seconds to get expiration time

            # Get localized subject
            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_account_locked",
                language=language,
            )

            # Get localized HTML body
            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_account_locked",
                language=language,
                first_name=first_name,
                failed_attempts=failed_attempts,
                lockout_reason=lockout_reason,
                lockout_ttl_seconds=lockout_ttl_seconds,
                lockout_until=lockout_until,
                locked_at=datetime.now(timezone.utc),
                support_email=settings.mailing.mail.from_email,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            # Send asynchronously
            await self._send_email_async(message, "account_locked", user.id)

            logger.info(
                f"Account locked email sent user_id={user.id} failed_attempts={failed_attempts} reason={lockout_reason}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send account locked email user_id={user.id} error={str(e)}",
                exc_info=True,
            )

    async def send_last_recovery_code_warning(
        self,
        user: User,
        remaining_count: int,
    ) -> None:
        """Send warning when user has 1 or 0 recovery codes left."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping last code warning user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_last_recovery_code",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_last_recovery_code",
                language=language,
                first_name=first_name,
                remaining_count=remaining_count,
                used_at=datetime.now(timezone.utc),
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "last_recovery_code", user.id)

            logger.info(f"Last recovery code warning sent user_id={user.id} remaining={remaining_count}")

        except Exception as e:
            logger.error(f"Failed to send last recovery code warning user_id={user.id} error={str(e)}", exc_info=True)

    async def send_mfa_disabled_notification(
        self,
        user: User,
        disabled_at: datetime,
    ) -> None:
        """Send notification when MFA is disabled."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping disabled notification user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_disabled",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_disabled",
                language=language,
                first_name=first_name,
                disabled_at=disabled_at,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "mfa_disabled", user.id)

            logger.info(f"MFA disabled notification sent user_id={user.id} disabled_at={disabled_at}")

        except Exception as e:
            logger.error(f"Failed to send MFA disabled notification user_id={user.id} error={str(e)}", exc_info=True)

    async def send_mfa_enabled_notification(
        self,
        user: User,
        enabled_at: datetime,
        recovery_codes_count: int,
    ) -> None:
        """Send notification when MFA is enabled."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping enabled notification user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_enabled",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_enabled",
                language=language,
                first_name=first_name,
                enabled_at=enabled_at,
                recovery_codes_count=recovery_codes_count,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "mfa_enabled", user.id)

            logger.info(f"MFA enabled notification sent user_id={user.id} enabled_at={enabled_at}")

        except Exception as e:
            logger.error(f"Failed to send MFA enabled notification user_id={user.id} error={str(e)}", exc_info=True)

    async def send_recovery_code_used_notification(
        self,
        user: User,
        used_at: datetime,
        remaining_codes: int,
        request_info: Optional[dict] = None,
    ) -> None:
        """Send notification when recovery code is used for login."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping recovery code used notification user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            # Extract request metadata
            ip_address = "Unknown"
            user_agent = "Unknown"
            if request_info:
                ip_address = request_info.get("ip_address", "Unknown")
                user_agent = request_info.get("user_agent", "Unknown")

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_recovery_code_used",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_recovery_code_used",
                language=language,
                first_name=first_name,
                used_at=used_at,
                remaining_codes=remaining_codes,
                ip_address=ip_address,
                user_agent=user_agent,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "recovery_code_used", user.id)

            logger.info(
                f"Recovery code used notification sent user_id={user.id} remaining={remaining_codes} ip={ip_address}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send recovery code used notification user_id={user.id} error={str(e)}", exc_info=True
            )

    async def send_failed_attempts_warning(
        self,
        user: User,
        failed_attempts: int,
        max_attempts: int,
    ) -> None:
        """Send warning after multiple failed MFA attempts."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping failed attempts warning user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_failed_attempts_warning",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_failed_attempts_warning",
                language=language,
                first_name=first_name,
                failed_attempts=failed_attempts,
                max_attempts=max_attempts,
                remaining_attempts=max_attempts - failed_attempts,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "failed_attempts_warning", user.id)

            logger.info(f"Failed attempts warning sent user_id={user.id} failed={failed_attempts}/{max_attempts}")

        except Exception as e:
            logger.error(f"Failed to send failed attempts warning user_id={user.id} error={str(e)}", exc_info=True)

    async def send_disable_failed_attempts_warning(
        self,
        user: User,
        failed_attempts: int,
        attempted_at: datetime,
    ) -> None:
        """Send warning when MFA disable attempt fails."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping disable failed attempts warning user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_disable_failed_attempts",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_disable_failed_attempts",
                language=language,
                first_name=first_name,
                failed_attempts=failed_attempts,
                attempted_at=attempted_at,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "disable_failed_attempts", user.id)

            logger.info(f"Disable failed attempts warning sent user_id={user.id} attempts={failed_attempts}")

        except Exception as e:
            logger.error(
                f"Failed to send disable failed attempts warning user_id={user.id} error={str(e)}", exc_info=True
            )

    async def send_recovery_codes_downloaded_notification(
        self,
        user: User,
        downloaded_at: datetime,
    ) -> None:
        """Send notification when recovery codes are downloaded."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping codes downloaded notification user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_recovery_codes_downloaded",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_recovery_codes_downloaded",
                language=language,
                first_name=first_name,
                downloaded_at=downloaded_at,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "codes_downloaded", user.id)

            logger.info(f"Recovery codes downloaded notification sent user_id={user.id}")

        except Exception as e:
            logger.error(
                f"Failed to send codes downloaded notification user_id={user.id} error={str(e)}", exc_info=True
            )

    async def send_recovery_codes_viewed_notification(
        self,
        user: User,
        viewed_at: datetime,
    ) -> None:
        """Send notification when recovery codes are viewed."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping codes viewed notification user_id={user.id}")
            return

        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            subject = self.mailing_service.get_localized_text_template(
                template_name="mfa_recovery_codes_viewed",
                language=language,
            )

            body = self.mailing_service.get_localized_html_template(
                template_name="mfa_recovery_codes_viewed",
                language=language,
                first_name=first_name,
                viewed_at=viewed_at,
                current_year=datetime.now().year,
            )

            message = MessageSchema(
                recipients=[email],
                subject=subject,
                body=body,
            )

            await self._send_email_async(message, "codes_viewed", user.id)

            logger.info(f"Recovery codes viewed notification sent user_id={user.id}")

        except Exception as e:
            logger.error(f"Failed to send codes viewed notification user_id={user.id} error={str(e)}", exc_info=True)

    async def _send_email_async(
        self,
        message: MessageSchema,
        notification_type: str,
        user_id: uuid.UUID,
    ) -> None:
        """Send email asynchronously without blocking."""
        try:
            asyncio.create_task(self.mailing_service.send(message))
            logger.debug(
                f"MFA notification email queued type={notification_type} user_id={user_id} subject='{message.subject}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to queue MFA notification email type={notification_type} user_id={user_id} error={str(e)}",
                exc_info=True,
            )
