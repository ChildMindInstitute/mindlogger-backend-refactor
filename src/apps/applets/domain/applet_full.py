import uuid

from pydantic import Field

from apps.activities.domain.activity_full import (
    ActivityFull,
    PublicActivityFull,
)
from apps.activity_flows.domain.flow_full import FlowFull, PublicFlowFull
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.enums import Language


class AppletFull(InternalModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: dict[Language, str] = Field(default_factory=dict)
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

    activities: list[ActivityFull] = Field(default_factory=list)
    activity_flows: list[FlowFull] = Field(default_factory=list)


class PublicAppletFull(PublicModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: dict[Language, str] = Field(default_factory=dict)
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

    activities: list[PublicActivityFull] = Field(default_factory=list)
    activity_flows: list[PublicFlowFull] = Field(default_factory=list)
