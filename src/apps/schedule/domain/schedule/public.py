import uuid

from apps.schedule.domain.schedule import BaseEvent, BasePeriodicity
from apps.shared.domain import PublicModel

__all__ = [
    "PublicPeriodicity",
    "PublicEvent",
    "ActivityEventCount",
    "FlowEventCount",
    "PublicEventCount",
    "PublicEventByUser",
]


class PublicPeriodicity(PublicModel, BasePeriodicity):
    pass


class PublicEvent(PublicModel, BaseEvent):
    id: uuid.UUID
    periodicity: PublicPeriodicity
    user_id: uuid.UUID | None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None


class ActivityEventCount(PublicModel):
    count: int
    activity_id: uuid.UUID
    activity_name: str


class FlowEventCount(PublicModel):
    count: int
    flow_id: uuid.UUID
    flow_name: str


class PublicEventCount(PublicModel):
    activity_events: list[ActivityEventCount] | None
    flow_events: list[FlowEventCount] | None


class PublicEventByUser(PublicModel):
    applet_id: uuid.UUID
    events: list[PublicEvent] | None
