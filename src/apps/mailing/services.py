from fastapi_mail import ConnectionConfig, FastMail

from apps.mailing.domain import MessageSchema
from config import settings


class MailingService:
    """A singleton realization of a Mailng service."""

    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)

        return getattr(cls, "_instance")

    def __init__(self) -> None:
        if self._initialized is True:
            return

        self._connection = ConnectionConfig(
            MAIL_USERNAME=settings.mailing.mail.username,
            MAIL_PASSWORD=settings.mailing.mail.password,
            MAIL_SERVER=settings.mailing.mail.server,
            MAIL_PORT=settings.mailing.mail.port,
            MAIL_STARTTLS=settings.mailing.mail.starttls,
            MAIL_SSL_TLS=settings.mailing.mail.ssl_tls,
            MAIL_FROM=settings.mailing.mail.from_email,
            MAIL_FROM_NAME=settings.mailing.mail.from_name,
        )

        self._initialized = True

    async def send(self, message: MessageSchema) -> None:
        fm = FastMail(self._connection)
        await fm.send_message(message)
