from typing import Optional

from pydantic import BaseModel


class FrontendUrlsSettings(BaseModel):
    web_base: str = "web.mindlogger.org"
    admin_base: str = "admin.frontend.com"
    invitation_send: str = "invitation"
    password_recovery_send: str = "password-recovery"
    public_link: str = "public"
    private_link: str = "join"
    transfer_link: str = "transferOwnership"
    create_account: str = "auth/signup"


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


class JsonLdConverterSettings(BaseModel):
    """Configure json-ld converter service settings."""

    protocol_password: str = ""
