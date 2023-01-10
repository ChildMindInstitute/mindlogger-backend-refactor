import uuid

from pydantic import Field

from apps.shared.domain import InternalModel

__all__ = ["Activity", "ActivityItem"]


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
    items: list[ActivityItem] = Field(default_factory=list)
