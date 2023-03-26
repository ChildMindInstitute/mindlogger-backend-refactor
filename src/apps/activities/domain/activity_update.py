import uuid

from pydantic import Field

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
)
from apps.activities.domain.response_values import ResponseValueConfig
from apps.shared.domain import InternalModel


class ActivityItemUpdate(InternalModel):
    id: uuid.UUID | None
    question: dict[str, str]
    response_type: ResponseType
    response_values: ResponseValueConfig
    config: ResponseTypeConfig
    name: str


class PreparedActivityItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_id: uuid.UUID
    question: dict[str, str]
    response_type: str
    response_values: ResponseValueConfig
    config: ResponseTypeConfig
    name: str


class ActivityUpdate(InternalModel):
    id: uuid.UUID | None
    name: str
    key: uuid.UUID
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemUpdate]
    is_hidden: bool = False
