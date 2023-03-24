import uuid

from pydantic import Field, validator

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
    TextConfig,
)
from apps.shared.domain import InternalModel, PublicModel


class _BaseActivityItem(InternalModel):
    id: uuid.UUID
    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    response_values: dict | list | None
    config: ResponseTypeConfig = Field(default_factory=TextConfig)
    order: int
    name: str = ""

    @validator("name")
    def validate_name(cls, value):
        # name must contain only alphanumeric symbols or underscore
        if not value.replace("_", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric symbols or underscore"
            )
        return value


class ActivityItem(_BaseActivityItem):
    activity_id: uuid.UUID


class ActivityItemPublic(_BaseActivityItem, PublicModel):
    pass


class ActivityItemDetail(ActivityItem):
    question: str  # type: ignore[assignment]


class ActivityItemDetailPublic(ActivityItemPublic):
    question: str  # type: ignore[assignment]
