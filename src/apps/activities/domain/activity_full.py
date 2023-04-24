import uuid

from pydantic import Field

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel, PublicModel


class ActivityItemFull(BaseActivityItem, InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    order: int


class ActivityFull(ActivityBase, InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    items: list[ActivityItemFull] = Field(default_factory=list)
    order: int


class PublicActivityItemFull(BaseActivityItem, PublicModel):
    id: uuid.UUID
    order: int


class PublicActivityFull(ActivityBase, PublicModel):
    id: uuid.UUID
    items: list[PublicActivityItemFull] = Field(default_factory=list)
