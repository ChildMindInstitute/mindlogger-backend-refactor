"""MFA email notification service.

Handles email notifications for MFA security events:
- CRITICAL: Account lockout, last recovery code, MFA disabled
- HIGH: MFA enabled, recovery code used, failed attempts
- MEDIUM: Recovery codes viewed/downloaded

All notifications are sent asynchronously via RabbitMQ to ensure non-blocking execution.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from apps.authentication.services.mfa_helpers import (
    get_user_display_name,
    get_user_email,
    get_user_language,
)
from apps.authentication.tasks import send_mfa_email_task
from apps.users.domain import User
from config import settings
from infrastructure.logger import logger


class MFANotificationService:
    """Sends MFA-related email notifications via RabbitMQ.

    All email notifications are queued asynchronously through RabbitMQ,
    ensuring that:
    - Email sending never blocks API responses
    - Failed emails can be retried automatically
    - Email load is distributed across worker processes
    """

    def _format_datetime_for_template(self, dt: datetime) -> str:
        """Format datetime for email templates."""
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")

    def _prepare_template_params(self, params: dict) -> dict:
        """Convert datetime objects to formatted strings for RabbitMQ serialization.

        Also adds current_year to all templates.
        """
        prepared: dict = {"current_year": datetime.now().year}
        for key, value in params.items():
            if isinstance(value, datetime):
                prepared[key] = self._format_datetime_for_template(value)
            else:
                prepared[key] = value
        return prepared

    async def _queue_email(
        self,
        notification_type: str,
        user: User,
        template_params: dict,
    ) -> None:
        """Queue an email notification task to RabbitMQ."""
        try:
            language = get_user_language(user)
            first_name = get_user_display_name(user)
            email = get_user_email(user)

            # Prepare template params (convert datetimes to formatted strings)
            prepared_params = self._prepare_template_params(template_params)

            # Queue the task to RabbitMQ
            await send_mfa_email_task.kiq(
                notification_type=notification_type,
                user_id=str(user.id),
                user_email=email,
                user_first_name=first_name,
                language=language,
                template_params=prepared_params,
            )

            logger.debug(f"MFA notification queued to RabbitMQ type={notification_type} user_id={user.id}")

        except Exception as e:
            # Log but don't raise - we don't want email queuing failures to break the main flow
            logger.error(
                f"Failed to queue MFA notification type={notification_type} user_id={user.id} error={str(e)}",
                exc_info=True,
            )

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

        # Calculate lockout expiration time
        lockout_until = None
        if lockout_ttl_seconds:
            lockout_until = datetime.now(timezone.utc) + timedelta(seconds=lockout_ttl_seconds)

        await self._queue_email(
            notification_type="mfa/mfa_account_locked",
            user=user,
            template_params={
                "failed_attempts": failed_attempts,
                "lockout_reason": lockout_reason,
                "lockout_ttl_seconds": lockout_ttl_seconds,
                "lockout_until": lockout_until,
                "locked_at": datetime.now(timezone.utc),
                "support_email": settings.mailing.mail.from_email,
            },
        )

        logger.info(
            f"Account locked email queued user_id={user.id} failed_attempts={failed_attempts} reason={lockout_reason}"
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

        await self._queue_email(
            notification_type="mfa/mfa_last_recovery_code",
            user=user,
            template_params={
                "remaining_count": remaining_count,
                "used_at": datetime.now(timezone.utc),
            },
        )

        logger.info(f"Last recovery code warning queued user_id={user.id} remaining={remaining_count}")

    async def send_mfa_disabled_notification(
        self,
        user: User,
        disabled_at: datetime,
    ) -> None:
        """Send notification when MFA is disabled."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping disabled notification user_id={user.id}")
            return

        await self._queue_email(
            notification_type="mfa/mfa_disabled",
            user=user,
            template_params={
                "disabled_at": disabled_at,
            },
        )

        logger.info(f"MFA disabled notification queued user_id={user.id} disabled_at={disabled_at}")

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

        await self._queue_email(
            notification_type="mfa/mfa_enabled",
            user=user,
            template_params={
                "enabled_at": enabled_at,
                "recovery_codes_count": recovery_codes_count,
            },
        )

        logger.info(f"MFA enabled notification queued user_id={user.id} enabled_at={enabled_at}")

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

        # Extract request metadata
        ip_address = "Unknown"
        user_agent = "Unknown"
        if request_info:
            ip_address = request_info.get("ip_address", "Unknown")
            user_agent = request_info.get("user_agent", "Unknown")

        await self._queue_email(
            notification_type="mfa/mfa_recovery_code_used",
            user=user,
            template_params={
                "used_at": used_at,
                "remaining_codes": remaining_codes,
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

        logger.info(
            f"Recovery code used notification queued user_id={user.id} remaining={remaining_codes} ip={ip_address}"
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

        await self._queue_email(
            notification_type="mfa/mfa_failed_attempts_warning",
            user=user,
            template_params={
                "failed_attempts": failed_attempts,
                "max_attempts": max_attempts,
                "remaining_attempts": max_attempts - failed_attempts,
            },
        )

        logger.info(f"Failed attempts warning queued user_id={user.id} failed={failed_attempts}/{max_attempts}")

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

        await self._queue_email(
            notification_type="mfa/mfa_disable_failed_attempts",
            user=user,
            template_params={
                "failed_attempts": failed_attempts,
                "attempted_at": attempted_at,
            },
        )

        logger.info(f"Disable failed attempts warning queued user_id={user.id} attempts={failed_attempts}")

    async def send_recovery_codes_downloaded_notification(
        self,
        user: User,
        downloaded_at: datetime,
    ) -> None:
        """Send notification when recovery codes are downloaded."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping codes downloaded notification user_id={user.id}")
            return

        await self._queue_email(
            notification_type="mfa/mfa_recovery_codes_downloaded",
            user=user,
            template_params={
                "downloaded_at": downloaded_at,
            },
        )

        logger.info(f"Recovery codes downloaded notification queued user_id={user.id}")

    async def send_recovery_codes_viewed_notification(
        self,
        user: User,
        viewed_at: datetime,
    ) -> None:
        """Send notification when recovery codes are viewed."""
        if not settings.mfa.enable_email_notifications:
            logger.debug(f"MFA notifications disabled, skipping codes viewed notification user_id={user.id}")
            return

        await self._queue_email(
            notification_type="mfa/mfa_recovery_codes_viewed",
            user=user,
            template_params={
                "viewed_at": viewed_at,
            },
        )

        logger.info(f"Recovery codes viewed notification queued user_id={user.id}")
