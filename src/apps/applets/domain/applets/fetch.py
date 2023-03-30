import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


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


class Activity(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    order: int


class ActivityItem(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    question: dict[str, str]
    response_type: str
    response_values: list | dict | None
    config: dict = dict()
    order: int


class ActivityFlow(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    order: int


class ActivityFlowItem(InternalModel):
    id: uuid.UUID
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID
    order: int
