from pydantic import root_validator

from apps.schedule.domain.schedule.base import BaseEvent, BasePeriodicity
from apps.shared.domain import InternalModel

__all__ = ["EventRequest", "PeriodicityRequest"]


class PeriodicityRequest(BasePeriodicity, InternalModel):
    pass


class EventRequest(BaseEvent, InternalModel):
    peroidicity: PeriodicityRequest
    user_id: int | None
    activity_id: int | None
    flow_id: int | None

    @root_validator
    def validate_optional_fields(cls, values):
        if not (bool(values.get("activity_id")) ^ bool(values.get("flow_id"))):
            raise ValueError(
                """Either activity_id or flow_id must be provided"""
            )
        return values
