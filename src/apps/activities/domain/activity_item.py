import uuid

from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel, PublicModel


class ActivityItem(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID
    id: uuid.UUID
    order: int


class ActivityItemPublic(BaseActivityItem, PublicModel):
    id: uuid.UUID


class ActivityItemDetail(ActivityItem):
    question: str  # type: ignore[assignment]


class ActivityItemDetailPublic(ActivityItemPublic):
    question: str  # type: ignore[assignment]
