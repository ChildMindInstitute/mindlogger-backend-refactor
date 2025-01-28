import uuid
from datetime import date

from pydantic import Field, root_validator

from apps.schedule.domain.constants import PeriodicityType
from apps.schedule.domain.schedule.base import BaseEvent, BaseNotificationSetting, BaseReminderSetting
from apps.schedule.errors import SelectedDateRequiredError
from apps.shared.domain import InternalModel

__all__ = [
    "Event",
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
        description="If type is WEEKLY, MONTHLY or ONCE," " selectedDate must be set.",
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
    version: str | None = None


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
        description="If type is WEEKLY, MONTHLY or ONCE," " selectedDate must be set.",
    )
    user_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None = None
    flow_id: uuid.UUID | None = None
    version: str | None = None
