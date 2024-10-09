from fastapi_mail import ConnectionConfig, FastMail
from jinja2 import Environment, PackageLoader, select_autoescape, TemplateNotFound

from apps.mailing.domain import MessageSchema
from config import settings


class TestMail:
    """
    Mailing class for tests to mock and check emails
    """

    mails: list[MessageSchema] = []

    def __init__(self, connection):
        self.connection = connection

    async def send_message(self, message: MessageSchema):
        self.mails.insert(0, message)

    @classmethod
    def clear_mails(cls):
        cls.mails = []


class MailingService:
    """A singleton realization of a Mailing service."""

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
        self.env = Environment(
            loader=PackageLoader("apps.mailing", "static/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )

        self._initialized = True

    async def send(self, message: MessageSchema) -> None:
        mailing_class = FastMail
        if settings.env == "testing":
            mailing_class = TestMail
        fm = mailing_class(self._connection)
        await fm.send_message(message)

    def get_localized_html_template(self, _template_name: str, _language: str, **kwargs) -> str:
        kwargs["language"] = _language
        try:
            return self.env.get_template(f"{_template_name}_{_language}.html").render(**kwargs)
        except TemplateNotFound as e:
            if _language != "en":
                return self.get_localized_html_template(_template_name, "en", **kwargs)
            raise
