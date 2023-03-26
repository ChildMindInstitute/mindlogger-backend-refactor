import uuid

from pydantic import Field

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
)
from apps.activities.domain.response_values import ResponseValueConfig
from apps.shared.domain import InternalModel


class ActivityItemCreate(InternalModel):
    name: str
    question: dict[str, str]
    response_type: ResponseType
    response_values: ResponseValueConfig
    config: ResponseTypeConfig


class PreparedActivityItemCreate(InternalModel):
    activity_id: uuid.UUID
    name: str
    question: dict[str, str]
    response_type: str
    response_values: ResponseValueConfig
    config: ResponseTypeConfig


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
