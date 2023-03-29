import uuid

from pydantic import Field
from apps.activities.domain.activity_item import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemFull(BaseActivityItem, InternalModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    order: int


class ActivityFull(InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemFull] = Field(default_factory=list)
    is_hidden: bool = False
    ordering: int
