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
    email: str
    device_id: str
    limit: PositiveInt = 1


class NotificationLogCreate(_NotificationLogBase, InternalModel):
    notification_descriptions: list[dict] | None
    notification_in_queue: list[dict] | None
    scheduled_notifications: list[dict] | None

    @validator(
        "notification_descriptions",
        "notification_in_queue",
        "scheduled_notifications",
        pre=True,
    )
    def convert_string_to_list(cls, v):
        """Convert legacy JSON string format to array format for backward compatibility.
        
        Mobile apps < v1.0.8 send notification fields as JSON strings.
        This validator ensures compatibility by converting strings to arrays.
        """
        if v is None:
            return None

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    return [parsed]
                return None
            except json.JSONDecodeError:
                # Handle malformed JSON gracefully
                return None

        if isinstance(v, list):
            return v

        return None

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
