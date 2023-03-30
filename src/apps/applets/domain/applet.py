import datetime
import uuid

from pydantic import Field, PositiveInt

from apps.activities.domain.activity import (
    ActivityDetail,
    ActivityDetailPublic,
    ActivityDuplicate,
)
from apps.activity_flows.domain.flow import (
    FlowDetail,
    FlowDetailPublic,
    FlowDuplicate,
)
from apps.shared.domain import InternalModel, PublicModel
from apps.workspaces.domain.constants import DataRetention


class Theme(InternalModel):
    id: uuid.UUID
    name: str
    logo: str
    background_image: str
    primary_color: str
    secondary_color: str
    tertiary_color: str
    public: bool
    allow_rename: bool
    creator_id: uuid.UUID


class Applet(InternalModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None


class ThemePublic(PublicModel):
    id: uuid.UUID
    name: str
    logo: str
    background_image: str
    primary_color: str
    secondary_color: str
    tertiary_color: str
    public: bool


class AppletPublic(PublicModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AppletDetail(Applet):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivityDetail] = Field(default_factory=list)
    activity_flows: list[FlowDetail] = Field(default_factory=list)
    theme: Theme | None = None


class AppletDuplicate(Applet):
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivityDuplicate] = Field(default_factory=list)
    activity_flows: list[FlowDuplicate] = Field(default_factory=list)
    theme: Theme | None = None


class AppletInfo(Applet):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    theme: Theme | None


class AppletDetailPublic(AppletPublic):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivityDetailPublic] = Field(default_factory=list)
    activity_flows: list[FlowDetailPublic] = Field(default_factory=list)
    theme: ThemePublic | None = None


class AppletInfoPublic(AppletPublic):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    theme: ThemePublic | None


class AppletName(InternalModel):
    name: str
    exclude_applet_id: uuid.UUID | None


class AppletUniqueName(PublicModel):
    name: str


class AppletDataRetention(InternalModel):
    period: PositiveInt
    retention: DataRetention
