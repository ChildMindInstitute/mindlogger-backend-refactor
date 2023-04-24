import uuid

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemCreate(BaseActivityItem, InternalModel):
    pass


class PreparedActivityItemCreate(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID


class ActivityCreate(ActivityBase, InternalModel):
    key: uuid.UUID
    items: list[ActivityItemCreate]
