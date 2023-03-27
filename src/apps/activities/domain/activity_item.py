import uuid

from pydantic import Field

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
    TextConfig,
)
from apps.shared.domain import InternalModel, PublicModel


class ActivityItem(InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    answers: dict | list | None
    config: ResponseTypeConfig = Field(default_factory=TextConfig)
    ordering: int


class ActivityItemPublic(PublicModel):
    id: uuid.UUID
    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    answers: dict | list | None
    config: ResponseTypeConfig = Field(default_factory=TextConfig)
    ordering: int


class ActivityItemDetail(ActivityItem):
    question: str  # type: ignore[assignment]


class ActivityItemDetailPublic(ActivityItemPublic):
    question: str  # type: ignore[assignment]
