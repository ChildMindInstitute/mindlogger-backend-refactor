import datetime
import uuid
from pydantic import Field

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_full import ActivityItemFull
from apps.shared.domain import InternalModel


class ActivityItemMigratedFull(ActivityItemFull):
    extra_fields: dict = Field(default_factory=dict)


class ActivityMigratedFull(ActivityBase, InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    order: int
    created_at: datetime.datetime
    extra_fields: dict = Field(default_factory=dict)
    items: list[ActivityItemMigratedFull] = Field(default_factory=list)
