import json

from pydantic import BaseModel, root_validator, validator
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "NotificationLogCreate",
    "PublicNotificationLog",
    "NotificationLogQuery",
]


class _NotificationLogBase(BaseModel):
    user_id: str
    device_id: str


class NotificationLogQuery(_NotificationLogBase):
    limit: PositiveInt = 1


class _NotificationLogInit(_NotificationLogBase):
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

    @root_validator
    def validate_json_fields(cls, values):
        if not any(
            [
                values.get("notification_descriptions"),
                values.get("notification_in_queue"),
                values.get("scheduled_notifications"),
            ]
        ):
            raise ValueError(
                """At least one of 3 optional fields
                (notification_descriptions,
                notification_in_queue,
                scheduled_notifications) must be provided"""
            )
        return values


class NotificationLogCreate(_NotificationLogInit, InternalModel):
    pass


class PublicNotificationLog(_NotificationLogInit, PublicModel):
    """Public NotificationLog model."""

    id: PositiveInt
