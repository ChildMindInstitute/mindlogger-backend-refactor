import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel


class ActivityItem(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    question: dict[str, str] = Field(default_factory=dict)
    response_type: str
    answers: dict | list | None
    color_palette: str
    timer: int
    has_token_value: bool
    is_skippable: bool
    has_alert: bool
    has_score: bool
    is_random: bool
    is_able_to_move_to_previous: bool
    has_text_response: bool
    ordering: int


class ActivityPublic(PublicModel):
    id: uuid.UUID
    question: dict[str, str] = Field(default_factory=dict)
    response_type: str
    answers: dict | list | None
    color_palette: str
    timer: int
    has_token_value: bool
    is_skippable: bool
    has_alert: bool
    has_score: bool
    is_random: bool
    is_able_to_move_to_previous: bool
    has_text_response: bool
    ordering: int


class ActivityItemDetail(ActivityItem):
    question: str  # type: ignore[assignment]


class ActivityItemDetailPublic(ActivityPublic):
    question: str  # type: ignore[assignment]
