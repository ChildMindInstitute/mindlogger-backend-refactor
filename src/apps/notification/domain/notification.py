from typing import Union

from pydantic import BaseModel, root_validator
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
    limit: Union[PositiveInt, None]


class PublicNotificationLog(_NotificationLogBase, PublicModel):
    """Public notification log model."""

    id: PositiveInt
    action_type: str
    notification_descriptions: Union[str, None]
    notification_in_queue: Union[str, None]
    scheduled_notifications: Union[str, None]


class NotificationLogCreate(_NotificationLogBase, InternalModel):
    action_type: str
    notification_descriptions: Union[str, None]
    notification_in_queue: Union[str, None]
    scheduled_notifications: Union[str, None]

    def __init__(self, **data: dict):
        if not any(
            [
                "notification_descriptions" in data,
                "notification_in_queue" in data,
                "scheduled_notifications" in data,
            ]
        ):
            raise TypeError(
                """Value needed for at least one field ('notification_descriptions', 'notification_in_queue', 'scheduled_notifications')"""
            )
        super().__init__(**data)


class NotificationLog(NotificationLogCreate):
    id: PositiveInt
    notification_descriptions_updated: bool
    notifications_in_queue_updated: bool
    scheduled_notifications_updated: bool
