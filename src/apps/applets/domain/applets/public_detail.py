import uuid

from pydantic import Field

from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.response_type_config import PerformanceTaskType, ResponseTypeConfig
from apps.activities.domain.response_values import ResponseValueConfig
from apps.activities.domain.scores_reports import ScoresAndReports, SubscaleSetting
from apps.shared.domain import PublicModel


class ActivityItem(PublicModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    question: dict[str, str]
    response_type: str
    response_values: ResponseValueConfig | None
    config: ResponseTypeConfig
    order: int
    is_hidden: bool | None
    conditional_logic: ConditionalLogic | None = None
    allow_edit: bool | None = None
    name: str


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
    items: list[ActivityItem] = Field(default_factory=list)
    scores_and_reports: ScoresAndReports | None = None
    subscale_setting: SubscaleSetting | None = None
    performance_task_type: PerformanceTaskType | None = None
    report_included_item_name: str | None = None
    is_performance_task: bool = False
    auto_assign: bool | None = True


class ActivityFlowItem(PublicModel):
    id: uuid.UUID
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID
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
    report_included_activity_name: str | None = None
    report_included_item_name: str | None = None
    auto_assign: bool | None = True


class Encryption(PublicModel):
    public_key: str
    prime: str
    base: str
    account_id: str


class Applet(PublicModel):
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
    encryption: Encryption | None
