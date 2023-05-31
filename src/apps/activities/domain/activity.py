import uuid
from datetime import datetime

from pydantic import Field

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item import (
    ActivityItemDuplicate,
    ActivityItemSingleLanguageDetail,
    ActivityItemSingleLanguageDetailPublic,
)
from apps.shared.domain import InternalModel, PublicModel


class Activity(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int


class ActivityDuplicate(ActivityBase, InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    order: int
    items: list[ActivityItemDuplicate] = Field(default_factory=list)


class ActivityPublic(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int


class ActivitySingleLanguageDetail(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    created_at: datetime


class ActivitySingleLanguageDetailPublic(ActivityBase, PublicModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    created_at: datetime


class ActivitySingleLanguageWithItemsDetail(ActivityBase, InternalModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    items: list[ActivityItemSingleLanguageDetail] = Field(default_factory=list)
    created_at: datetime


class ActivitySingleLanguageWithItemsDetailPublic(ActivityBase, PublicModel):
    id: uuid.UUID
    order: int
    description: str  # type: ignore[assignment]
    items: list[ActivityItemSingleLanguageDetailPublic] = Field(
        default_factory=list
    )
    created_at: datetime
