import uuid

from pydantic import Field, root_validator

from apps.schedule.domain.constants import PeriodicityType
from apps.schedule.domain.schedule.base import (
    BaseEvent,
    BasePeriodicity,
    BaseNotificationSetting,
    BaseReminderSetting,
)
from apps.shared.domain import PublicModel

__all__ = ["EventRequest", "PeriodicityRequest"]


class PeriodicityRequest(BasePeriodicity, PublicModel):
    pass


class NotificationSettingRequest(BaseNotificationSetting, PublicModel):
    pass


class ReminderSettingRequest(BaseReminderSetting, PublicModel):
    pass


class Notification(PublicModel):

    notifications: list[NotificationSettingRequest] | None = None
    reminder: ReminderSettingRequest | None = None


class EventRequest(BaseEvent, PublicModel):
    periodicity: PeriodicityRequest
    respondent_id: uuid.UUID | None
    activity_id: uuid.UUID | None = Field(
        None,
        description="If flow_id is not set, activity_id must be set.",
    )
    flow_id: uuid.UUID | None = Field(
        None,
        description="If activity_id is not set, flow_id must be set.",
    )
    notification: Notification | None = None

    @root_validator
    def validate_optional_fields(cls, values):
        if not (bool(values.get("activity_id")) ^ bool(values.get("flow_id"))):
            raise ValueError(
                """Either activity_id or flow_id must be provided"""
            )

        # if periodicity is Always, one_time_completion must be set.
        if (
            values.get("periodicity").type == PeriodicityType.ALWAYS
            and not type(values.get("one_time_completion")) == bool
        ):
            raise ValueError(
                """one_time_completion must be set if periodicity is ALWAYS"""
            )

        # if periodicity is not Always, start_time and end_time, access_before_schedule must be set. # noqa: E501
        if (
            values.get("periodicity").type != PeriodicityType.ALWAYS
            and not values.get("start_time")
            and not values.get("end_time")
            and not type(values.get("access_before_schedule")) == bool
        ):
            raise ValueError(
                """start_time, end_time, access_before_schedule must be set if periodicity is not ALWAYS"""  # noqa: E501
            )
        return values
