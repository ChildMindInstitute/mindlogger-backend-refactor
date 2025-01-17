from datetime import date, time, timedelta

from pydantic import BaseModel, Field, NonNegativeInt, root_validator

from apps.schedule.domain.constants import NotificationTriggerType, PeriodicityType, TimerType
from apps.schedule.errors import (
    AtTimeFieldRequiredError,
    FromTimeToTimeRequiredError,
    SelectedDateRequiredError,
    TimerRequiredError,
)


class BasePeriodicity(BaseModel):
    """Periodicity of an event"""

    type: PeriodicityType
    start_date: date | None
    end_date: date | None
    selected_date: date | None = Field(
        None,
        description="If type is WEEKLY, MONTHLY or ONCE, selectedDate must be set.",
    )

    @root_validator
    def validate_periodicity(cls, values):
        if values.get("type") in [
            PeriodicityType.ONCE,
            PeriodicityType.WEEKLY,
            PeriodicityType.MONTHLY,
        ] and not values.get("selected_date"):
            raise SelectedDateRequiredError()
        return values


class BaseEvent(BaseModel):
    """Event of a schedule"""

    start_time: time | None = Field(
        None,
        description="If periodicity is not AlwaysAvailable, must be set.",
    )
    end_time: time | None = Field(
        None,
        description="If periodicity is not AlwaysAvailable, must be set.",
    )
    access_before_schedule: bool | None = Field(
        None,
        description="If periodicity is not AlwaysAvailable, must be set.",
    )
    one_time_completion: bool | None = Field(
        None,
        description="If periodicity is AlwaysAvailable, must be set.",
    )
    timer: timedelta | None = Field(
        None,
        description="If timer_type is TIMER or IDLE, timer must be set.",
        example="00:01:00",
    )
    timer_type: TimerType

    @root_validator
    def validate_timer(cls, values):
        if values.get("timer_type") != TimerType.NOT_SET and not values.get("timer"):
            raise TimerRequiredError()

        return values


class BaseNotificationSetting(BaseModel):
    """Notification settings of an event"""

    trigger_type: NotificationTriggerType
    from_time: time | None = Field(
        None,
        description="If triggerType is RANDOM, fromTime must be set.",
    )
    to_time: time | None = Field(
        None,
        description="If triggerType is RANDOM, toTime must be set.",
    )
    at_time: time | None = Field(
        None,
        description="If triggerType is FIXED, atTime must be set.",
    )
    order: int | None = None

    @root_validator
    def validate_notification(cls, values):
        if values.get("trigger_type") == NotificationTriggerType.FIXED:
            if not values.get("at_time"):
                raise AtTimeFieldRequiredError()
        elif values.get("trigger_type") == NotificationTriggerType.RANDOM:
            if not values.get("from_time") or not values.get("to_time"):
                raise FromTimeToTimeRequiredError()
        return values


class BaseReminderSetting(BaseModel):
    """Reminder settings of an event"""

    activity_incomplete: NonNegativeInt
    reminder_time: time
