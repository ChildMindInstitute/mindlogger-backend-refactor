from pydantic import PositiveInt

from apps.schedule.domain.schedule.base import BaseEvent, BasePeriodicity
from apps.shared.domain import InternalModel

__all__ = [
    "Event",
    "Periodicity",
    "UserEvent",
    "ActivityEvent",
    "FlowEvent",
    "EventCreate",
    "EventUpdate",
    "UserEventCreate",
    "ActivityEventCreate",
    "FlowEventCreate",
    "EventFull",
]


class EventCreate(BaseEvent, InternalModel):
    periodicity_id: PositiveInt
    applet_id: PositiveInt


class EventUpdate(EventCreate):
    pass


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


class EventFull(InternalModel, BaseEvent):
    id: PositiveInt
    periodicity: Periodicity
    user_id: int | None
    activity_id: int | None
    flow_id: int | None


# class EventByUser(InternalModel):
#     applet_id: PositiveInt
#     events: list[EventFull] | None
