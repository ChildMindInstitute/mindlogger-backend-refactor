"""Background tasks for MFA email notifications using RabbitMQ."""

from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from broker import broker
from infrastructure.logger import logger


@broker.task
async def send_mfa_email_task(
    notification_type: str,
    user_id: str,
    user_email: str,
    user_first_name: str,
    language: str,
    template_params: dict,
) -> None:
    """Background task to send MFA notification emails via RabbitMQ."""
    try:
        mailing_service = MailingService()

        # Get localized subject
        subject = mailing_service.get_localized_text_template(
            template_name=notification_type,
            language=language,
        )

        # Get localized HTML body with template parameters
        body = mailing_service.get_localized_html_template(
            template_name=notification_type,
            language=language,
            first_name=user_first_name,
            **template_params,
        )

        message = MessageSchema(
            recipients=[user_email],
            subject=subject,
            body=body,
        )

        # Send email synchronously within the task
        await mailing_service.send(message)

        logger.info(
            f"MFA notification email sent via RabbitMQ type={notification_type} user_id={user_id} subject='{subject}'"
        )

    except Exception as e:
        logger.error(
            f"Failed to send MFA notification email in task type={notification_type} user_id={user_id} error={str(e)}",
            exc_info=True,
        )
        # Re-raise to trigger taskiq retry mechanism
        raise
