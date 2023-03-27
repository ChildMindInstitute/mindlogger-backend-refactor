import uuid

from pydantic import Field

from apps.activities.domain.activity_item import (
    ActivityItemDetail,
    ActivityItemDetailPublic,
)
from apps.shared.domain import InternalModel, PublicModel


class Activity(InternalModel):
    id: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    ordering: float
    is_hidden: bool | None = False


class ActivityPublic(PublicModel):
    id: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    ordering: float


class ActivityDetail(Activity):
    description: str  # type: ignore[assignment]


class ActivityExtendedDetail(ActivityDetail):
    items: list[ActivityItemDetail] = Field(default_factory=list)


class ActivityDetailPublic(ActivityPublic):
    description: str  # type: ignore[assignment]


class ActivityExtendedDetailPublic(ActivityDetailPublic):
    items: list[ActivityItemDetailPublic] = Field(default_factory=list)
