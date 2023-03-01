import datetime
import uuid

from pydantic import Field

from apps.activities.domain.activity import (
    ActivityDetail,
    ActivityDetailPublic,
)
from apps.activity_flows.domain.flow import FlowDetail, FlowDetailPublic
from apps.shared.domain import InternalModel, PublicModel


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

    activities: list[ActivityDetail] = Field(default_factory=list)
    activity_flows: list[FlowDetail] = Field(default_factory=list)


class AppletInfo(Applet):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]


class AppletDetailPublic(AppletPublic):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]

    activities: list[ActivityDetailPublic] = Field(default_factory=list)
    activity_flows: list[FlowDetailPublic] = Field(default_factory=list)


class AppletInfoPublic(AppletPublic):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]


class AppletName(InternalModel):
    name: str
    exclude_applet_id: uuid.UUID | None


class AppletUniqueName(PublicModel):
    name: str
