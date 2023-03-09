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
    once = "ONCE"
    daily = "DAILY"
    weekly = "WEEKLY"
    weekdays = "WEEKDAYS"
    monthly = "MONTHLY"
    always = "ALWAYS"


class TimerType(str, Enum):
    not_set = "NOT_SET"
    timer = "TIMER"
    idle = "IDLE"


class DefaultEvent(BaseModel):
    start_time: time = time.min
    end_time: time = time.max
    all_day: bool = True
    access_before_schedule: bool = True
    one_time_completion: bool = False
    timer: timedelta = timedelta()
    timer_type: TimerType = TimerType.not_set
    periodicity: dict = {
        "type": PeriodicityType.always,
        "start_date": date.min,
        "end_date": date.max,
        "interval": 0,
    }
    user_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None


class AvailabilityType(str, Enum):
    AlwaysAvailable = "AlwaysAvailable"
    ScheduledAccess = "ScheduledAccess"
