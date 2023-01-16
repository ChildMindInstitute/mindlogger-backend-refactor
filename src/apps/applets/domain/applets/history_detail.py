import uuid

from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel


class ActivityItem(InternalModel):
    id: int
    activity_id: str
    question: dict[str, str]
    response_type: str
    answers: list
    color_palette: str = ""
    timer: int = 0
    has_token_value: bool = False
    is_skippable: bool = False
    has_alert: bool = False
    has_score: bool = False
    is_random: bool = False
    is_able_to_move_to_previous: bool = False
    has_text_response: bool = False
    ordering: float


class Activity(InternalModel):
    id: int
    applet_id: str
    guid: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    ordering: float
    items: list[ActivityItem] = Field(default_factory=list)


class ActivityFlowItem(InternalModel):
    id: int
    activity_flow_id: str
    activity_id: str
    ordering: int
    activity: Activity | None


class ActivityFlow(InternalModel):
    id: int
    guid: uuid.UUID
    name: str
    applet_id: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    ordering: int
    items: list[ActivityFlowItem] = Field(default_factory=list)


class Applet(InternalModel):
    id: int
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: PositiveInt | None = None
    report_server_ip: str = ""
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""
    activities: list[Activity] = Field(default_factory=list)
    activity_flows: list[ActivityFlow] = Field(default_factory=list)
