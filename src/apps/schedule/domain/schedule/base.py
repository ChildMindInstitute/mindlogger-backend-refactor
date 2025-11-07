from datetime import date, time, timedelta
from typing import Self

from pydantic import BaseModel, Field, NonNegativeInt, model_validator

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
    start_date: date | None = None
    end_date: date | None = None
    selected_date: date | None = Field(
        None,
        description="If type is WEEKLY, MONTHLY or ONCE, selectedDate must be set.",
    )

    @model_validator(mode="after")
    def validate_periodicity(self) -> Self:
        if self.type in [
            PeriodicityType.ONCE,
            PeriodicityType.WEEKLY,
            PeriodicityType.MONTHLY,
        ] and not self.selected_date:
            raise SelectedDateRequiredError()
        return self


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
        examples=["00:01:00"],
    )
    timer_type: TimerType

    @model_validator(mode="after")
    def validate_timer(self) -> Self:
        if self.timer_type != TimerType.NOT_SET and not self.timer:
            raise TimerRequiredError()
        return self


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

    @model_validator(mode="after")
    def validate_notification(self) -> Self:
        if self.trigger_type == NotificationTriggerType.FIXED:
            if not self.at_time:
                raise AtTimeFieldRequiredError()
        elif self.trigger_type == NotificationTriggerType.RANDOM:
            if not self.from_time or not self.to_time:
                raise FromTimeToTimeRequiredError()
        return self


class BaseReminderSetting(BaseModel):
    """Reminder settings of an event"""

    activity_incomplete: NonNegativeInt
    reminder_time: time
