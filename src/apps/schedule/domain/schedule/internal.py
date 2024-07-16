import uuid

from apps.schedule.db.schemas import EventSchema
from apps.schedule.domain.schedule.base import BaseEvent, BaseNotificationSetting, BasePeriodicity, BaseReminderSetting
from apps.shared.domain import InternalModel

__all__ = [
    "Event",
    "Periodicity",
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
    periodicity_id: uuid.UUID
    applet_id: uuid.UUID

class EventWithActivityOrFlowId(EventSchema):
    activity_id: uuid.UUID | None = None
    flow_id: uuid.UUID | None = None

class EventUpdate(EventCreate):
    pass


class Event(EventCreate, InternalModel):
    id: uuid.UUID


class Periodicity(BasePeriodicity, InternalModel):
    id: uuid.UUID


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
    periodicity: Periodicity
    user_id: uuid.UUID | None = None
    activity_id: uuid.UUID | None = None
    flow_id: uuid.UUID | None = None
