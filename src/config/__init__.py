from pathlib import Path

from pydantic import BaseSettings

from config.alerts import AlertsSettings
from config.anonymous_respondent import AnonymousRespondent
from config.applet import AppletEMASettings
from config.authentication import AuthenticationSettings
from config.cdn import CDNSettings
from config.cors import CorsSettings
from config.database import DatabaseSettings
from config.logs import Logs
from config.mailing import MailingSettings
from config.multiinformant import MultiInformantSettings
from config.notification import FirebaseCloudMessagingSettings
from config.opentelemetry import OpenTelemetrySettings
from config.rabbitmq import RabbitMQSettings
from config.redis import RedisSettings
from config.secret import SecretSettings
from config.sentry import SentrySettings
from config.service import JsonLdConverterSettings, ServiceSettings
from config.superuser import SuperAdmin
from config.task import AnswerEncryption, AudioFileConvert, ImageConvert


# NOTE: Settings powered by pydantic
# https://pydantic-docs.helpmanual.io/usage/settings/
class Settings(BaseSettings):
    root_dir: Path
    apps_dir: Path
    locale_dir: Path
    default_language: str = "en"
    content_length_limit: int | None = 150 * 1024 * 1024

    debug: bool = False
    commit_id: str = "Not assigned"
    version: str = "Not assigned"

    env: str = "dev"

    # Service
    service: ServiceSettings = ServiceSettings()

    # Authentication
    authentication: AuthenticationSettings

    # Encryption
    secrets: SecretSettings = SecretSettings()

    # CORS policy
    cors: CorsSettings = CorsSettings()

    # Database
    database: DatabaseSettings = DatabaseSettings()

    # Redis
    redis: RedisSettings = RedisSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()

    # Mailing
    mailing: MailingSettings = MailingSettings()

    # CDN configs
    cdn: CDNSettings = CDNSettings()

    # Sentry stuff
    sentry: SentrySettings = SentrySettings()

    # FCM Notification configs
    fcm: FirebaseCloudMessagingSettings = FirebaseCloudMessagingSettings()

    # json-ld converter settings
    jsonld_converter: JsonLdConverterSettings = JsonLdConverterSettings()

    # Alerts configs
    alerts: AlertsSettings = AlertsSettings()

    # NOTE: This config is used by SQLAlchemy for imports
    migrations_apps: list[str]

    super_admin = SuperAdmin()

    anonymous_respondent = AnonymousRespondent()

    task_answer_encryption = AnswerEncryption()
    task_audio_file_convert = AudioFileConvert()
    task_image_convert = ImageConvert()

    applet_ema = AppletEMASettings()

    logs: Logs = Logs()

    opentelemetry: OpenTelemetrySettings = OpenTelemetrySettings()

    multi_informant: MultiInformantSettings = MultiInformantSettings()

    @property
    def uploads_dir(self):
        return self.root_dir.parent / "uploads"

    class Config:
        env_nested_delimiter = "__"
        env_file = ".env"


# Load settings
settings = Settings(
    # NOTE: We would like to hardcode the root and applications directories
    #       to avoid overridding via environment variables
    root_dir=Path(__file__).parent.parent,
    apps_dir=Path(__file__).parent.parent / "apps",
    locale_dir=Path(__file__).parent.parent / "locale",
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
        "workspaces",
        "transfer_ownership",
        "alerts",
        "library",
        "authentication",
        "job",
        "subjects",
    ],
)
