import uuid

from apps.activities.domain.response_type_config import ResponseType
from apps.shared.domain import InternalModel


class ActivityItemHistory(InternalModel):
    id: uuid.UUID
    id_version: str
    activity_id: str
    header_image: str | None
    question: dict[str, str]
    response_type: ResponseType
    answers: dict | list | None
    config: dict
    ordering: int
    skippable_item: bool
    remove_availability_to_go_back: bool
