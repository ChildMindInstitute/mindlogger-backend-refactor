from pathlib import Path

from pydantic import BaseSettings

from config.authentication import AuthenticationSettings
from config.database import DatabaseSettings
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

    # Cache
    redis_url: str = "redis://redis"

    # DataBase
    database = DatabaseSettings()

    # Authentication
    authentication = AuthenticationSettings()

    # Sentry stuff
    sentry: SentrySettings = SentrySettings()

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
