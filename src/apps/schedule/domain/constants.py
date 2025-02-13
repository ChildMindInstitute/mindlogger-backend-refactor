import uuid
from datetime import time, timedelta
from enum import StrEnum

from pydantic import BaseModel

__all__ = [
    "PeriodicityType",
    "TimerType",
    "DefaultEvent",
    "AvailabilityType",
    "EventType",
]


class PeriodicityType(StrEnum):
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    WEEKDAYS = "WEEKDAYS"
    MONTHLY = "MONTHLY"
    ALWAYS = "ALWAYS"


class EventType(StrEnum):
    ACTIVITY = "activity"
    FLOW = "flow"


class TimerType(StrEnum):
    NOT_SET = "NOT_SET"
    TIMER = "TIMER"
    IDLE = "IDLE"


class DefaultEvent(BaseModel):
    start_time: time = time(0, 0)
    end_time: time = time(23, 59)
    access_before_schedule: bool = False
    one_time_completion: bool = False
    timer: timedelta = timedelta()
    timer_type: TimerType = TimerType.NOT_SET
    periodicity: dict = {
        "type": PeriodicityType.ALWAYS,
        "start_date": None,
        "end_date": None,
        "selected_date": None,
    }
    respondent_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None


class AvailabilityType(StrEnum):
    ALWAYS_AVAILABLE = "AlwaysAvailable"
    SCHEDULED_ACCESS = "ScheduledAccess"


class NotificationTriggerType(StrEnum):
    FIXED = "FIXED"
    RANDOM = "RANDOM"
