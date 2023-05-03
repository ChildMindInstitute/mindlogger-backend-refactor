import uuid

from apps.activities.domain.response_type_config import (
    ResponseType,
    ResponseTypeConfig,
)
from apps.shared.domain import InternalModel


class ActivityItemHistory(InternalModel):
    id: uuid.UUID
    id_version: str
    activity_id: str
    name: str
    question: dict[str, str]
    response_type: ResponseType
    response_values: dict | list | None
    config: dict
    order: int
