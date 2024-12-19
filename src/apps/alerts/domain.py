import datetime
import uuid
from enum import Enum

from pydantic import Field, validator

from apps.shared.domain import InternalModel, PublicModel, ResponseMulti, dict_keys_to_camel_case

__all__ = [
    "Alert",
    "AlertPublic",
    "AlertMessage",
]


class AlertTypes(str, Enum):
    ANSWER_ALERT = "answer"
    INTEGRATION_ALERT = "integration"


class Alert(InternalModel):
    id: uuid.UUID
    is_watched: bool
    applet_id: uuid.UUID
    applet_name: str
    version: str
    secret_id: str
    activity_id: uuid.UUID | None
    activity_item_id: uuid.UUID | None
    message: str
    created_at: datetime.datetime
    answer_id: uuid.UUID | None
    encryption: dict
    image: str
    workspace: str
    respondent_id: uuid.UUID
    subject_id: uuid.UUID | None
    type: AlertTypes = Field(default=AlertTypes.ANSWER_ALERT)


class AlertPublic(PublicModel):
    id: uuid.UUID
    is_watched: bool
    applet_id: uuid.UUID
    applet_name: str
    version: str
    secret_id: str
    activity_id: uuid.UUID | None
    activity_item_id: uuid.UUID | None
    message: str
    created_at: datetime.datetime
    answer_id: uuid.UUID | None
    encryption: dict
    image: str
    workspace: str
    respondent_id: uuid.UUID
    subject_id: uuid.UUID | None
    type: AlertTypes = Field(default=AlertTypes.ANSWER_ALERT)

    @validator("encryption", pre=True)
    def convert_response_values_keys(cls, response_values):
        if response_values and isinstance(response_values, dict):
            return dict_keys_to_camel_case(response_values)
        return response_values


class AlertMessage(InternalModel):
    id: uuid.UUID
    respondent_id: uuid.UUID
    subject_id: uuid.UUID | None
    applet_id: uuid.UUID
    version: str
    message: str
    created_at: datetime.datetime
    activity_id: uuid.UUID | None
    activity_item_id: uuid.UUID | None
    answer_id: uuid.UUID | None
    type: AlertTypes = Field(default=AlertTypes.ANSWER_ALERT)


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
    subject_id: str | None
    type: AlertTypes = Field(default=AlertTypes.ANSWER_ALERT)


class AlertResponseMulti(ResponseMulti[AlertPublic]):
    not_watched: int
