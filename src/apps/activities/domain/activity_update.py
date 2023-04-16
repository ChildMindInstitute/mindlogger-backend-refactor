import uuid

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemUpdate(BaseActivityItem, InternalModel):
    id: uuid.UUID | None


class PreparedActivityItemUpdate(BaseActivityItem, InternalModel):
    id: uuid.UUID | None
    activity_id: uuid.UUID


class ActivityUpdate(ActivityBase, InternalModel):
    id: uuid.UUID | None
    key: uuid.UUID
    items: list[ActivityItemUpdate]
