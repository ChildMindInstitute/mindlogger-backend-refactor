from datetime import date, time, timedelta

from pydantic import BaseModel, root_validator

from apps.schedule.domain.constants import PeriodicityType, TimerType
from apps.shared.errors import ValidationError


class BasePeriodicity(BaseModel):
    """Periodicity of an event"""

    type: PeriodicityType
    start_date: date
    end_date: date
    interval: int

    @root_validator
    def validate_periodicity(cls, values):
        if values.get("type") == PeriodicityType.weekly:
            if values.get("interval") < 1 or values.get("interval") > 7:
                raise ValidationError("Interval must be between 1 and 7")
        elif values.get("type") == PeriodicityType.monthly:
            if values.get("interval") < 1 or values.get("interval") > 31:
                raise ValidationError("Interval must be between 1 and 31")
        else:
            if values.get("interval") != 0:
                raise ValidationError("Interval must be 0")
        return values


class BaseEvent(BaseModel):
    """Event of a schedule"""

    start_time: time
    end_time: time
    all_day: bool
    access_before_schedule: bool
    one_time_completion: bool
    timer: timedelta
    timer_type: TimerType
