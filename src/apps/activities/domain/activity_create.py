import uuid

from pydantic import Field

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemCreate(BaseActivityItem, InternalModel):
    extra_fields: dict = Field(default_factory=dict)


class PreparedActivityItemCreate(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID


class ActivityCreate(ActivityBase, InternalModel):
    key: uuid.UUID
    items: list[ActivityItemCreate]
    extra_fields: dict = Field(default_factory=dict)
