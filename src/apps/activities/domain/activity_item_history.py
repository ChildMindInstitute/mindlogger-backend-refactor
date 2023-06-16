import uuid

from apps.activities.domain.response_type_config import ResponseType
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
    is_hidden: bool | None = False
    conditional_logic: dict | None = None
    allow_edit: bool | None = None


class ActivityItemHistoryChange(InternalModel):
    name: str | None = None
    changes: list[str] | None = None
