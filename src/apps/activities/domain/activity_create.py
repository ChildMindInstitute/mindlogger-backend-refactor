import uuid

from pydantic import Field

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
)
from apps.shared.domain import InternalModel


class ActivityItemCreate(InternalModel):
    header_image: str | None
    question: dict[str, str]
    response_type: ResponseType
    answers: list
    config: ResponseTypeConfig
    skippable_item: bool = False
    remove_availability_to_go_back: bool = False


class PreparedActivityItemCreate(InternalModel):
    activity_id: uuid.UUID
    question: dict[str, str]
    response_type: str
    answers: list
    config: ResponseTypeConfig
    skippable_item: bool = False
    remove_availability_to_go_back: bool = False


class ActivityCreate(InternalModel):
    name: str
    key: uuid.UUID
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemCreate]
    is_hidden: bool = False
