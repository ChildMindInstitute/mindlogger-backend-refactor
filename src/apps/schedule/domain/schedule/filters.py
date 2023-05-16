import uuid

from apps.shared.domain import InternalModel

__all__ = [
    "EventQueryParams",
]


class EventQueryParams(InternalModel):
    respondent_id: uuid.UUID | None
