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


class EventCreate(BaseEvent, InternalModel):
    periodicity_id: PositiveInt
    applet_id: PositiveInt


class Event(EventCreate, InternalModel):
    id: PositiveInt


class Periodicity(BasePeriodicity, InternalModel):
    id: PositiveInt


class UserEventCreate(InternalModel):
    user_id: PositiveInt
    event_id: PositiveInt


class UserEvent(UserEventCreate, InternalModel):
    """UserEvent of a schedule"""

    id: PositiveInt


class ActivityEventCreate(InternalModel):
    activity_id: PositiveInt
    event_id: PositiveInt


class ActivityEvent(ActivityEventCreate, InternalModel):
    """ActivityEvent of a schedule"""

    id: PositiveInt


class FlowEventCreate(InternalModel):
    flow_id: PositiveInt
    event_id: PositiveInt


class FlowEvent(FlowEventCreate, InternalModel):
    """FlowEvent of a schedule"""

    id: PositiveInt
