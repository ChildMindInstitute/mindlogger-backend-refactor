import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ActivityHistory",
    "ActivityHistoryChange",
    "PublicActivityHistoryChange",
]


class ActivityHistory(InternalModel):
    id: uuid.UUID
    applet_id: str
    id_version: str
    name: str
    description: dict
    splash_screen: str
    image: str
    show_all_at_once: bool
    is_skippable: bool
    is_reviewable: bool
    response_is_editable: bool
    ordering: int
    created_at: datetime.datetime


class ActivityHistoryChange(InternalModel):
    name: str | None = None
    description: str | None = None
    splash_screen: str | None = None
    image: str | None = None
    show_all_at_once: str | None = None
    is_skippable: str | None = None
    is_reviewable: str | None = None
    response_is_editable: str | None = None
    ordering: str | None = None


class PublicActivityHistoryChange(PublicModel):
    name: str | None = None
    description: dict | None = None
    splash_screen: str | None = None
    image: str | None = None
    show_all_at_once: str | None = None
    is_skippable: str | None = None
    is_reviewable: str | None = None
    response_is_editable: str | None = None
    ordering: str | None = None
