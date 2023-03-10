from datetime import date, time, timedelta

from pydantic import BaseModel, Field, root_validator

from apps.schedule.domain.constants import PeriodicityType, TimerType
from apps.shared.errors import ValidationError


class BasePeriodicity(BaseModel):
    """Periodicity of an event"""

    type: PeriodicityType
    start_date: date
    end_date: date
    interval: int = Field(
        ...,
        description="Must be between 1 and 7 for WEEKLY. Must be between 1 and 31 for MONTHLY. Otherwise, must be 0",  # noqa: E501
    )

    @root_validator
    def validate_periodicity(cls, values):
        if values.get("type") == PeriodicityType.WEEKLY:
            if values.get("interval") < 1 or values.get("interval") > 7:
                raise ValidationError(
                    message="Interval must be between 1 and 7"
                )
        elif values.get("type") == PeriodicityType.MONTHLY:
            if values.get("interval") < 1 or values.get("interval") > 31:
                raise ValidationError(
                    message="Interval must be between 1 and 31"
                )
        else:
            if values.get("interval") != 0:
                raise ValidationError(message="Interval must be 0")
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
