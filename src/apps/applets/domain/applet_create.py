import uuid

from pydantic import Field

from apps.activities.domain.activity_create import ActivityCreate
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.shared.domain import InternalModel


class AppletCreate(InternalModel):
    display_name: str
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
    password: str

    activities: list[ActivityCreate]
    activity_flows: list[FlowCreate]


class AppletDuplicatePassword(InternalModel):
    password: str
