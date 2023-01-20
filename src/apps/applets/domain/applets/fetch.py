import uuid

from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel


class Applet(InternalModel):
    id: int
    display_name: str
    version: str
    description: dict[str, str] = Field(default_factory=dict)
    about: dict[str, str] = Field(default_factory=dict)
    image: str = ""
    watermark: str = ""
    theme_id: PositiveInt | None = None
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""


class Activity(InternalModel):
    id: int
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


class ActivityItem(InternalModel):
    id: int
    activity_id: int
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


class ActivityFlow(InternalModel):
    id: int
    guid: uuid.UUID
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    ordering: int


class ActivityFlowItem(InternalModel):
    id: int
    activity_flow_id: int
    activity_id: int
    ordering: int
