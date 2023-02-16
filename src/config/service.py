from typing import Optional

from pydantic import BaseModel


class FrontendUrlsSettings(BaseModel):
    web_base: str = "web.frontend.com"
    admin_base: str = "admin.frontend.com"
    invitation_send: str = "invite"
    password_recovery_send: str = "password-recovery"
    public_link: str = "public"
    private_link: str = "join"


class ServiceUrlsSettings(BaseModel):
    """Configure all public urls."""

    docs: str = "/docs"
    openapi: Optional[str] = None
    redoc: str = "/redoc"
    frontend: FrontendUrlsSettings = FrontendUrlsSettings()


class ServiceSettings(BaseModel):
    """Configure public service settings."""

    name: str = "mindlogger-service"
    port: int = 8000
    urls: ServiceUrlsSettings = ServiceUrlsSettings()
