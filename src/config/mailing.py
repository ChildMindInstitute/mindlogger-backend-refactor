from pydantic import BaseModel, EmailStr


class MailSettings(BaseModel):
    username: str = "mailhog"
    password: str = "mailhog"
    server: str = "fcm.mail.server"
    port: int = 1025
    starttls: bool = False
    ssl_tls: bool = False
    from_email: EmailStr = EmailStr("fcm@email.com")
    from_name: str = "FCM"


class MailingSettings(BaseModel):
    """Configure mailnig settings for the mindlogger"""

    mail: MailSettings = MailSettings()

    # Currently these settings are not used
    use_credentials: bool = False
    validate_certs: bool = False
