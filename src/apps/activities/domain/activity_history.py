import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ActivityHistory",
    "ActivityHistoryChange",
    "PublicActivityHistoryChange",
]


class ActivityHistory(InternalModel):
    id: int
    applet_id: str
    id_version: str
    guid: uuid.UUID
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
    name: str | None
    description: dict | None
    splash_screen: str | None
    image: str | None
    show_all_at_once: str | None
    is_skippable: str | None
    is_reviewable: str | None
    response_is_editable: str | None
    ordering: str | None


class PublicActivityHistoryChange(PublicModel, ActivityHistoryChange):
    pass
