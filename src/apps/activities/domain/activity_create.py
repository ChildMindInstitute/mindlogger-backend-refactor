import uuid

from pydantic import Field

from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemCreate(BaseActivityItem, InternalModel):
    extra_fields: dict = Field(default_factory=dict)


class PreparedActivityItemCreate(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID


class ActivityCreate(InternalModel):
    name: str
    key: uuid.UUID
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemCreate]
    is_hidden: bool = False
    extra_fields: dict = Field(default_factory=dict)
