import uuid
from datetime import datetime

from pydantic import Field, validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.domain.custom_validation import (
    validate_is_performance_task,
    validate_performance_task_type,
)
from apps.activities.domain.response_type_config import PerformanceTaskType
from apps.shared.domain import InternalModel, PublicModel


class ActivityItemFull(BaseActivityItem, InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    order: int
    extra_fields: dict = Field(default_factory=dict)


class ActivityItemHistoryFull(BaseActivityItem, InternalModel):
    id: uuid.UUID
    id_version: str
    activity_id: str
    order: int
    extra_fields: dict = Field(default_factory=dict)


class ActivityFull(ActivityBase, InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    items: list[ActivityItemFull] = Field(default_factory=list)
    order: int
    created_at: datetime
    extra_fields: dict = Field(default_factory=dict)


class PublicActivityItemFull(BaseActivityItem, PublicModel):
    id: uuid.UUID
    order: int


class PublicActivityFull(ActivityBase, PublicModel):
    id: uuid.UUID
    items: list[PublicActivityItemFull] = Field(default_factory=list)
    created_at: datetime
    is_performance_task: bool = False
    performance_task_type: PerformanceTaskType | None = None

    @validator("is_performance_task", always=True)
    def validate_is_performance_task_full(cls, value, values):
        return validate_is_performance_task(value, values)

    @validator("performance_task_type", always=True)
    def validate_performance_task_type_full(cls, value, values):
        return validate_performance_task_type(value, values)
