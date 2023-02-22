from pathlib import Path

from pydantic import BaseSettings

from config.authentication import AuthenticationSettings
from config.cdn import CDNSettings
from config.cors import CorsSettings
from config.database import DatabaseSettings
from config.mailing import MailingSettings
from config.notification import NotificationSettings
from config.redis import RedisSettings
from config.sentry import SentrySettings
from config.service import ServiceSettings


# NOTE: Settings powered by pydantic
# https://pydantic-docs.helpmanual.io/usage/settings/
class Settings(BaseSettings):
    root_dir: Path
    apps_dir: Path

    debug: bool = True
    commit_id: str = "Not assigned"

    env: str = "dev"

    # Service
    service: ServiceSettings = ServiceSettings()

    # Authentication
    authentication: AuthenticationSettings = AuthenticationSettings()

    # CORS policy
    cors: CorsSettings = CorsSettings()

    # Database
    database: DatabaseSettings = DatabaseSettings()

    # Redis
    redis: RedisSettings = RedisSettings()

    # Mailing
    mailing: MailingSettings = MailingSettings()

    # CDN configs
    cdn: CDNSettings = CDNSettings()

    # Sentry stuff
    sentry: SentrySettings = SentrySettings()

    # FCM Notification configs
    notification: NotificationSettings = NotificationSettings()

    # NOTE: This config is used by SQLAlchemy for imports
    migrations_apps: list[str]

    class Config:
        env_nested_delimiter = "__"
        env_file = ".env"


# Load settings
settings = Settings(
    # NOTE: We would like to hardcode the root and applications directories
    #       to avoid overridding via environment variables
    root_dir=Path(__file__).parent.parent,
    apps_dir=Path(__file__).parent.parent / "apps",
    migrations_apps=[
        "users",
        "applets",
        "activities",
        "activity_flows",
        "themes",
        "logs",
        "schedule",
        "answers",
        "folders",
        "answers",
        "invitations",
    ],
)
