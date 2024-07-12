import enum

from pydantic import Field

from apps.shared.domain import PublicModel


class EmergencyMessageType(str, enum.Enum):
    info = "info"
    warning = "warning"
    blocker = "blocker"


class EmergencyMessage(PublicModel):
    message: str | None = None
    message_type: EmergencyMessageType | None = Field(None, alias="type")
    dismissible: bool = True


class AppInfoOS(PublicModel):
    name: str
    version: str


class AppInfo(PublicModel):
    os: AppInfoOS
    app_version: str
