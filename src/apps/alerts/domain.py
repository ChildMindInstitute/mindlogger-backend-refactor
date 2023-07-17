import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "Alert",
    "AlertPublic",
    "AlertMessage",
]


class Alert(InternalModel):
    id: uuid.UUID
    is_watched: bool
    applet_id: uuid.UUID
    applet_name: str
    version: str
    secret_id: str
    activity_id: uuid.UUID
    activity_item_id: uuid.UUID
    message: str
    created_at: datetime.datetime
    answer_id: uuid.UUID


class AlertPublic(PublicModel):
    id: uuid.UUID
    is_watched: bool
    applet_id: uuid.UUID
    applet_name: str
    version: str
    secret_id: str
    activity_id: uuid.UUID
    activity_item_id: uuid.UUID
    message: str
    created_at: datetime.datetime
    answer_id: uuid.UUID


class AlertMessage(InternalModel):
    id: uuid.UUID
    respondent_id: uuid.UUID
    applet_id: uuid.UUID
    version: str
    message: str
    created_at: datetime.datetime
    activity_id: uuid.UUID
    activity_item_id: uuid.UUID
    answer_id: uuid.UUID
