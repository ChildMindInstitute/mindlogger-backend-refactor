from pydantic import BaseModel, EmailStr


class MailSettings(BaseModel):
    username: str = "mailpit"
    password: str = "mailpit"
    server: str = "fcm.mail.server"
    port: int = 1025
    starttls: bool = False
    ssl_tls: bool = False
    from_email: EmailStr = "noreply@gettingcurious.com"
    from_name: str = "Curious"


class MailingSettings(BaseModel):
    """Configure mailnig settings for the mindlogger"""

    mail: MailSettings = MailSettings()

    # Currently these settings are not used
    use_credentials: bool = False
    validate_certs: bool = False
