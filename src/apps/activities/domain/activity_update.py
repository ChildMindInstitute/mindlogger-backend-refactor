import uuid

from pydantic import Field

from apps.activities.domain.activity_item import BaseActivityItem
from apps.shared.domain import InternalModel


class ActivityItemUpdate(BaseActivityItem):
    id: uuid.UUID | None


class PreparedActivityItemUpdate(BaseActivityItem):
    id: uuid.UUID | None
    activity_id: uuid.UUID


class ActivityUpdate(InternalModel):
    id: uuid.UUID | None
    name: str
    key: uuid.UUID
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemUpdate]
    is_hidden: bool = False
