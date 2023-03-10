import uuid
from datetime import date, time, timedelta
from enum import Enum

from pydantic import BaseModel

__all__ = [
    "PeriodicityType",
    "TimerType",
    "DefaultEvent",
]


class PeriodicityType(str, Enum):
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    WEEKDAYS = "WEEKDAYS"
    MONTHLY = "MONTHLY"
    ALWAYS = "ALWAYS"


class TimerType(str, Enum):
    NOT_SET = "NOT_SET"
    TIMER = "TIMER"
    IDLE = "IDLE"


class DefaultEvent(BaseModel):
    start_time: time = time.min
    end_time: time = time.max
    all_day: bool = True
    access_before_schedule: bool = True
    one_time_completion: bool = False
    timer: timedelta = timedelta()
    timer_type: TimerType = TimerType.NOT_SET
    periodicity: dict = {
        "type": PeriodicityType.ALWAYS,
        "start_date": date.min,
        "end_date": date.max,
        "interval": 0,
    }
    user_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None


class AvailabilityType(str, Enum):
    ALWAYS_AVAILABLE = "AlwaysAvailable"
    SCHEDULED_ACCESS = "ScheduledAccess"
