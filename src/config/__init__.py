from os import getenv
from pathlib import Path

from pydantic import BaseSettings

from config.sentry import SentrySettings
from config.service import ServiceSettings, ServiceUrlsSettings


# NOTE: Settings powered by pydantic
# https://pydantic-docs.helpmanual.io/usage/settings/
class Settings(BaseSettings):
    root_dir: Path
    apps_dir: Path

    debug: bool = True

    env: str = "local"

    # Service
    service: ServiceSettings = ServiceSettings()

    database_url = getenv(
        "DATABASE_URL",
        default=(
            "postgresql+asyncpg://"
            "postgres:postgres@postgres:5432/mindlogger_backend"
        ),
    )

    # Cache
    redis_url: str = "redis://redis"

    # Authentication
    secret_key = getenv(
        "SECRET_KEY",
        default="e51bcf5f4cb8550ff3f6a8bb4dfe112a"
        "3da2cf5142929e1b281cd974c88fa66c",
    )
    algorithm = getenv(
        "ALGORITHM",
        default="HS256",
    )
    access_token_expire_minutes = getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        default=30,
    )

    # Sentry stuff
    sentry: SentrySettings = SentrySettings()

    # Providers

    class Config:
        env_nested_delimiter = "__"


# Load settings
settings = Settings(
    # NOTE: We would like to hardcode the root and applications directories
    #       to avoid overridding via environment variables
    root_dir=Path(__file__).parent.parent,
    apps_dir=Path(__file__).parent.parent / "apps",
    service=ServiceSettings(
        urls=ServiceUrlsSettings(
            openapi="/openapi.json",
        ),
    ),
)
