from datetime import date, time, timedelta

from pydantic import BaseModel, Field, root_validator

from apps.schedule.domain.constants import PeriodicityType, TimerType
from apps.shared.errors import ValidationError


class BasePeriodicity(BaseModel):
    """Periodicity of an event"""

    type: PeriodicityType
    start_date: date | None
    end_date: date | None
    selected_date: date | None = Field(
        None,
        description="If type is WEEKLY, MONTHLY or ONCE, selectedDate must be set",  # noqa: E501
    )

    @root_validator
    def validate_periodicity(cls, values):
        if values.get("type") in [
            PeriodicityType.ONCE,
            PeriodicityType.WEEKLY,
            PeriodicityType.MONTHLY,
        ] and not values.get("selected_date"):
            raise ValidationError(
                message="selected_date is required for this periodicity type"
            )
        return values


class BaseEvent(BaseModel):
    """Event of a schedule"""

    start_time: time
    end_time: time
    all_day: bool
    access_before_schedule: bool
    one_time_completion: bool
    timer: timedelta | None = Field(
        None,
        description="If timer_type is TIMER or IDLE, timer must be set",
    )
    timer_type: TimerType

    @root_validator
    def validate_timer(cls, values):
        if values.get("timer_type") in [
            TimerType.TIMER,
            TimerType.IDLE,
        ] and not values.get("timer"):
            raise ValidationError(
                message="timer is required for this timer type"
            )
        return values
