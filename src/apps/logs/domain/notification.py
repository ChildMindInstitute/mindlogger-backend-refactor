import json

from pydantic import BaseModel, validator
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "NotificationLogCreate",
    "NotificationLog",
    "PublicNotificationLog",
    "NotificationLogQuery",
]


class _NotificationLogBase(BaseModel):
    user_id: str
    device_id: str


class NotificationLogQuery(_NotificationLogBase):
    limit: PositiveInt | None


class NotificationLogCreate(_NotificationLogBase, InternalModel):
    action_type: str
    notification_descriptions: str | None
    notification_in_queue: str | None
    scheduled_notifications: str | None

    @validator(
        "notification_descriptions",
        "notification_in_queue",
        "scheduled_notifications",
    )
    def validate_json(cls, v):
        try:
            return json.dumps(json.loads(v))
        except Exception:
            raise ValueError("Invalid JSON")


class NotificationLog(NotificationLogCreate):
    id: PositiveInt
    notification_descriptions_updated: bool
    notifications_in_queue_updated: bool
    scheduled_notifications_updated: bool


class PublicNotificationLog(NotificationLogCreate, PublicModel):
    """Public NotificationLog model."""

    id: PositiveInt
