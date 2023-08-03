import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel, ResponseMulti

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
    encryption: dict
    image: str
    workspace: str
    respondent_id: uuid.UUID


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
    encryption: dict
    image: str
    workspace: str
    respondent_id: uuid.UUID


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


class AlertHandlerResult(InternalModel):
    id: str
    applet_id: str
    applet_name: str
    version: str
    secret_id: str
    activity_id: str
    activity_item_id: str
    message: str
    created_at: str
    answer_id: str
    encryption: dict
    image: str
    workspace: str
    respondent_id: str


class AlertResponseMulti(ResponseMulti[AlertPublic]):
    not_watched: int
