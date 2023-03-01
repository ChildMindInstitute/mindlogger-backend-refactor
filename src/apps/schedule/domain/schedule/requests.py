import uuid

from pydantic import root_validator

from apps.schedule.domain.schedule.base import BaseEvent, BasePeriodicity
from apps.shared.domain import PublicModel

__all__ = ["EventRequest", "PeriodicityRequest"]


class PeriodicityRequest(BasePeriodicity, PublicModel):
    pass


class EventRequest(BaseEvent, PublicModel):
    periodicity: PeriodicityRequest
    user_id: uuid.UUID | None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None

    @root_validator
    def validate_optional_fields(cls, values):
        if not (bool(values.get("activity_id")) ^ bool(values.get("flow_id"))):
            raise ValueError(
                """Either activity_id or flow_id must be provided"""
            )
        return values
