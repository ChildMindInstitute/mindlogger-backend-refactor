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
    name: str
    description: dict
    splash_screen: str
    image: str
    show_all_at_once: str
    is_skippable: str
    is_reviewable: str
    response_is_editable: str
    ordering: str


class PublicActivityHistoryChange(PublicModel, ActivityHistoryChange):
    pass
