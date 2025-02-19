import uuid
from datetime import date

from pydantic import NonNegativeInt, validator

from apps.schedule.domain.constants import AvailabilityType, NotificationTriggerType, PeriodicityType
from apps.schedule.domain.schedule import BaseEvent, BaseNotificationSetting, BasePeriodicity, BaseReminderSetting
from apps.schedule.errors import HourRangeError, MinuteRangeError
from apps.shared.domain import PublicModel

__all__ = [
    "PublicPeriodicity",
    "PublicEvent",
    "ActivityEventCount",
    "FlowEventCount",
    "PublicEventCount",
    "PublicEventByUser",
    "HourMinute",
    "TimerDto",
    "EventAvailabilityDto",
    "ScheduleEventDto",
]


class PublicPeriodicity(PublicModel, BasePeriodicity):
    pass


class PublicNotificationSetting(PublicModel, BaseNotificationSetting):
    id: uuid.UUID


class PublicReminderSetting(PublicModel, BaseReminderSetting):
    id: uuid.UUID


class PublicNotification(PublicModel):
    notifications: list[PublicNotificationSetting] | None = None
    reminder: PublicReminderSetting | None = None


class PublicEvent(PublicModel, BaseEvent):
    id: uuid.UUID
    periodicity: PublicPeriodicity
    respondent_id: uuid.UUID | None
    activity_id: uuid.UUID | None
    flow_id: uuid.UUID | None
    notification: PublicNotification | None = None
    version: str | None = None


class ActivityEventCount(PublicModel):
    count: int
    activity_id: uuid.UUID
    activity_name: str


class FlowEventCount(PublicModel):
    count: int
    flow_id: uuid.UUID
    flow_name: str


class PublicEventCount(PublicModel):
    activity_events: list[ActivityEventCount] | None
    flow_events: list[FlowEventCount] | None


class HourMinute(PublicModel):
    hours: NonNegativeInt
    minutes: NonNegativeInt

    @validator("hours")
    def validate_hour(cls, value):
        if value > 23:
            raise HourRangeError()
        return value

    @validator("minutes")
    def validate_minute(cls, value):
        if value > 59:
            raise MinuteRangeError()
        return value


class TimerDto(PublicModel):
    timer: HourMinute | None = None
    idleTimer: HourMinute | None = None


class ReminderSettingDTO(PublicModel):
    activity_incomplete: int
    reminder_time: HourMinute


class NotificationSettingDTO(PublicModel):
    trigger_type: NotificationTriggerType
    from_time: HourMinute | None = None
    to_time: HourMinute | None = None
    at_time: HourMinute | None = None


class NotificationDTO(PublicModel):
    notifications: list[NotificationSettingDTO] | None = None
    reminder: ReminderSettingDTO | None = None


class EventAvailabilityDto(PublicModel):
    oneTimeCompletion: bool | None = None
    periodicityType: PeriodicityType
    timeFrom: HourMinute | None = None
    timeTo: HourMinute | None = None
    allowAccessBeforeFromTime: bool | None = None
    startDate: date | None = None
    endDate: date | None = None


class ScheduleEventDto(PublicModel):
    id: uuid.UUID
    entityId: uuid.UUID
    availability: EventAvailabilityDto
    selectedDate: date | None = None
    timers: TimerDto
    availabilityType: AvailabilityType
    notificationSettings: NotificationDTO | None = None
    version: str | None = None


class PublicEventByUser(PublicModel):
    applet_id: uuid.UUID
    events: list[ScheduleEventDto] | None = None
