import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityItemUpdate(InternalModel):
    id: uuid.UUID | None
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


class ActivityUpdate(InternalModel):
    id: uuid.UUID | None
    key: uuid.UUID
    name: str
    description: dict[str, str]
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemUpdate]


class ActivityFlowItemUpdate(InternalModel):
    id: uuid.UUID | None = None
    activity_key: uuid.UUID


class ActivityFlowUpdate(InternalModel):
    id: uuid.UUID | None
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: list[ActivityFlowItemUpdate]


class AppletUpdate(InternalModel):
    display_name: str
    description: dict[str, str]
    about: dict[str, str]
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    report_server_ip: str = ""  # Fixme: ip address
    report_public_key: str = ""
    report_recipients: list[str] = Field(default_factory=list)
    report_include_user_id: bool = False
    report_include_case_id: bool = False
    report_email_body: str = ""

    activities: list[ActivityUpdate]
    activity_flows: list[ActivityFlowUpdate]
