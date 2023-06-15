import uuid

from pydantic import Field

from apps.shared.domain import PublicModel


class ActivityItem(PublicModel):
    id: uuid.UUID
    question: dict[str, str]
    response_type: str
    response_values: list | dict | None
    config: dict = dict()
    order: int
    name: str
    is_hidden: bool | None = False
    conditional_logic: dict | None = None
    allow_edit: bool | None = None


class Activity(PublicModel):
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
    is_hidden: bool = False
    scores_and_reports: dict | None = None
    subscale_setting: dict | None = None
    items: list[ActivityItem] = Field(default_factory=list)


class ActivityFlowItem(PublicModel):
    id: uuid.UUID
    order: int
    activity: Activity | None


class ActivityFlow(PublicModel):
    id: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    order: int
    items: list[ActivityFlowItem] = Field(default_factory=list)


class AppletDetailHistory(PublicModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    activities: list[Activity] = Field(default_factory=list)
    activity_flows: list[ActivityFlow] = Field(default_factory=list)
