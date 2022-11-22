from typing import Optional

from pydantic import BaseModel


class ServiceUrlsSettings(BaseModel):
    """Configure all public urls."""

    docs: Optional[str] = "/docs"
    openapi: Optional[str] = None
    redoc: Optional[str] = "/redoc"


class ServiceSettings(BaseModel):
    """Configure public service settings."""

    name: str = "mindlogger-service"
    port: int = 8000
    urls: ServiceUrlsSettings = ServiceUrlsSettings()
