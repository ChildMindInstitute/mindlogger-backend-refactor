from typing import Optional

from pydantic import BaseModel


class FrontendUrlsSettings(BaseModel):
    base: str = "frontend.com"
    invitation_send: str = "invite"


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
