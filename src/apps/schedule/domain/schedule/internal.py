import uuid
from datetime import date

from pydantic import Field, NonNegativeInt, root_validator

from apps.schedule.domain.constants import AvailabilityType, PeriodicityType, TimerType
from apps.schedule.domain.schedule.base import BaseEvent, BaseNotificationSetting, BaseReminderSetting
from apps.schedule.domain.schedule.public import (
    EventAvailabilityDto,
    HourMinute,
    NotificationDTO,
    NotificationSettingDTO,
    ReminderSettingDTO,
    ScheduleEventDto,
    TimerDto,
)
from apps.schedule.errors import SelectedDateRequiredError
from apps.shared.domain import InternalModel

__all__ = [
    "Event",
    "ScheduleEvent",
    "UserEvent",
    "ActivityEvent",
    "FlowEvent",
    "EventCreate",
    "EventUpdate",
    "UserEventCreate",
    "ActivityEventCreate",
    "FlowEventCreate",
    "EventFull",
    "NotificationSettingCreate",
    "NotificationSetting",
    "ReminderSettingCreate",
    "ReminderSetting",
]


class EventCreate(BaseEvent, InternalModel):
    applet_id: uuid.UUID
    periodicity: PeriodicityType
    start_date: date | None
    end_date: date | None
    selected_date: date | None = Field(
        None,
        description="If type is WEEKLY, MONTHLY or ONCE, selectedDate must be set.",
    )

    @root_validator
    def validate_periodicity(cls, values):
        if values.get("periodicity") in [
            PeriodicityType.ONCE,
            PeriodicityType.WEEKLY,
            PeriodicityType.MONTHLY,
        ] and not values.get("selected_date"):
            raise SelectedDateRequiredError()
        return values


class EventUpdate(EventCreate):
    pass


class Event(EventCreate, InternalModel):
    id: uuid.UUID
    version: str


class UserEventCreate(InternalModel):
    user_id: uuid.UUID
    event_id: uuid.UUID


class UserEvent(UserEventCreate, InternalModel):
    """UserEvent of a schedule"""

    id: uuid.UUID


class ActivityEventCreate(InternalModel):
    activity_id: uuid.UUID
    event_id: uuid.UUID


class ActivityEvent(ActivityEventCreate, InternalModel):
    """ActivityEvent of a schedule"""

    id: uuid.UUID


class FlowEventCreate(InternalModel):
    flow_id: uuid.UUID
    event_id: uuid.UUID


class FlowEvent(FlowEventCreate, InternalModel):
    """FlowEvent of a schedule"""

    id: uuid.UUID


class NotificationSettingCreate(BaseNotificationSetting, InternalModel):
    event_id: uuid.UUID


class NotificationSetting(NotificationSettingCreate, InternalModel):
    id: uuid.UUID


class ReminderSettingCreate(BaseReminderSetting, InternalModel):
    event_id: uuid.UUID


class ReminderSetting(ReminderSettingCreate, InternalModel):
    id: uuid.UUID


class EventFull(InternalModel, BaseEvent):
    id: uuid.UUID
    periodicity: PeriodicityType
    start_date: date | None
    end_date: date | None
    selected_date: date | None = Field(
        None,
        description="If type is WEEKLY, MONTHLY or ONCE, selectedDate must be set.",
    )
    user_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None = None
    flow_id: uuid.UUID | None = None
    version: str


class ScheduleEvent(EventFull):
    notifications: list[NotificationSetting] | None = None
    reminder: ReminderSetting | None = None

    def to_schedule_event_dto(self) -> ScheduleEventDto:
        """Convert event to dto."""
        timers = TimerDto(
            timer=HourMinute(
                hours=NonNegativeInt(self.timer.seconds // 3600 if self.timer else 0),
                minutes=NonNegativeInt(self.timer.seconds // 60 % 60 if self.timer else 0),
            )
            if self.timer_type == TimerType.TIMER
            else None,
            idleTimer=HourMinute(
                hours=NonNegativeInt(self.timer.seconds // 3600 if self.timer else 0),
                minutes=NonNegativeInt(self.timer.seconds // 60 % 60 if self.timer else 0),
            )
            if self.timer_type == TimerType.IDLE
            else None,
        )

        availability_type = (
            AvailabilityType.ALWAYS_AVAILABLE
            if self.periodicity == PeriodicityType.ALWAYS
            else AvailabilityType.SCHEDULED_ACCESS
        )

        availability = EventAvailabilityDto(
            oneTimeCompletion=self.one_time_completion,
            periodicityType=self.periodicity,
            timeFrom=HourMinute(
                hours=NonNegativeInt(self.start_time.hour if self.start_time else 0),
                minutes=NonNegativeInt(self.start_time.minute if self.start_time else 0),
            ),
            timeTo=HourMinute(
                hours=NonNegativeInt(self.end_time.hour if self.end_time else 0),
                minutes=NonNegativeInt(self.end_time.minute if self.end_time else 0),
            ),
            allowAccessBeforeFromTime=self.access_before_schedule,
            startDate=self.start_date,
            endDate=self.end_date,
        )

        notification_settings = None
        if self.notifications or self.reminder:
            notifications_dto = None
            reminder_dto = None
            if self.notifications:
                notifications_dto = [
                    NotificationSettingDTO(
                        trigger_type=notification.trigger_type,
                        from_time=HourMinute(
                            hours=NonNegativeInt(notification.from_time.hour),
                            minutes=NonNegativeInt(notification.from_time.minute),
                        )
                        if notification.from_time
                        else None,
                        to_time=HourMinute(
                            hours=NonNegativeInt(notification.to_time.hour),
                            minutes=NonNegativeInt(notification.to_time.minute),
                        )
                        if notification.to_time
                        else None,
                        at_time=HourMinute(
                            hours=NonNegativeInt(notification.at_time.hour),
                            minutes=NonNegativeInt(notification.at_time.minute),
                        )
                        if notification.at_time
                        else None,
                    )
                    for notification in self.notifications
                ]
            if self.reminder:
                reminder_dto = ReminderSettingDTO(
                    activity_incomplete=self.reminder.activity_incomplete,
                    reminder_time=HourMinute(
                        hours=NonNegativeInt(self.reminder.reminder_time.hour),
                        minutes=NonNegativeInt(self.reminder.reminder_time.minute),
                    ),
                )
            notification_settings = NotificationDTO(notifications=notifications_dto, reminder=reminder_dto)

        return ScheduleEventDto(
            id=self.id,
            entityId=self.activity_id if self.activity_id else self.flow_id,
            timers=timers,
            availabilityType=availability_type,
            availability=availability,
            selectedDate=self.selected_date,
            notificationSettings=notification_settings,
            version=self.version,
        )
