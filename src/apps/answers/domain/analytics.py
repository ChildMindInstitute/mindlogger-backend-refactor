import uuid
from enum import Enum

from apps.shared.domain import InternalModel


class AnalyticsResponseType(str, Enum):
    SINGLE_SELECT = "singleSelect"
    MULTI_SELECT = "multiSelect"
    SLIDER = "slider"


class DataValue(InternalModel):
    date: str
    value: int


class ResponseConfigOptions(InternalModel):
    name: str
    value: int


class ResponseConfig(InternalModel):
    options: list[ResponseConfigOptions] | None


class Response(InternalModel):
    name: str
    type: AnalyticsResponseType
    data: list[DataValue]
    response_config: ResponseConfig


class ActivitiesResponses(InternalModel):
    id: uuid.UUID
    name: str
    responses: list[Response]


class AnswersMobileData(InternalModel):
    applet_id: uuid.UUID
    activities_responses: list[ActivitiesResponses] | None = None
