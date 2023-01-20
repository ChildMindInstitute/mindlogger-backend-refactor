from datetime import date, time, timedelta

from pydantic import BaseModel

from apps.schedule.domain.constants import PeriodicityType, TimerType


class BasePeriodicity(BaseModel):
    """Periodicity of an event"""

    type: PeriodicityType
    start_date: date
    end_date: date
    interval: int


class BaseEvent(BaseModel):
    """Event of a schedule"""

    start_time: time
    end_time: time
    all_day: bool
    access_before_schedule: bool
    one_time_completion: bool
    timer: timedelta
    timer_type: TimerType
