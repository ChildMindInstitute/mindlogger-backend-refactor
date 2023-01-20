from pydantic import PositiveInt

from apps.schedule.domain.schedule.base import BaseEvent, BasePeriodicity
from apps.shared.domain import InternalModel

__all__ = [
    "Event",
    "Periodicity",
    "UserEvent",
    "ActivityEvent",
    "FlowEvent",
]


class Event(BaseEvent, InternalModel):
    id: PositiveInt


class Periodicity(BasePeriodicity, InternalModel):
    id: PositiveInt


class UserEvent(InternalModel):
    """UserEvent of a schedule"""

    user_id: PositiveInt
    event_id: PositiveInt
    id: PositiveInt


class ActivityEvent(InternalModel):
    """ActivityEvent of a schedule"""

    activity_id: PositiveInt
    event_id: PositiveInt
    id: PositiveInt


class FlowEvent(InternalModel):
    """FlowEvent of a schedule"""

    flow_id: PositiveInt
    event_id: PositiveInt
    id: PositiveInt
