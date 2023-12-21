import datetime
import json
import uuid

from pydantic import BaseModel, root_validator, validator
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "NotificationLogCreate",
    "PublicNotificationLog",
    "NotificationLogQuery",
]


class _NotificationLogBase(BaseModel):
    action_type: str
    user_id: str
    device_id: str


class NotificationLogQuery(BaseModel):
    # TODO: remove user_id field in the future and make email field required
    # currently we are supporting both (email is optional) while mobile is not
    # ready
    user_id: str
    email: str | None
    device_id: str
    limit: PositiveInt = 1


class NotificationLogCreate(_NotificationLogBase, InternalModel):
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
            if v is not None:
                return json.loads(v)
        except json.JSONDecodeError:
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


class PublicNotificationLog(_NotificationLogBase, PublicModel):
    """Public NotificationLog model."""

    id: uuid.UUID
    notification_descriptions: list | None
    notification_in_queue: list | None
    scheduled_notifications: list | None
    created_at: datetime.datetime

    @validator(
        "notification_descriptions",
        "notification_in_queue",
        "scheduled_notifications",
        pre=True,
    )
    def validate_json(cls, v):
        try:
            if isinstance(v, str):
                return json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON")
