import uuid

from pydantic import Field, root_validator

from apps.schedule.domain.constants import (
    NotificationTriggerType,
    PeriodicityType,
)
from apps.schedule.domain.schedule.base import (
    BaseEvent,
    BaseNotificationSetting,
    BasePeriodicity,
    BaseReminderSetting,
)
from apps.shared.domain import PublicModel

__all__ = [
    "EventRequest",
    "PeriodicityRequest",
    "NotificationSettingRequest",
    "ReminderSettingRequest",
]


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
        if values.get("periodicity").type != PeriodicityType.ALWAYS:
            if (
                not bool(values.get("start_time"))
                or not bool(values.get("end_time"))
                or not type(values.get("access_before_schedule")) == bool
            ):
                raise ValueError(
                    """start_time, end_time, access_before_schedule must be set if periodicity is not ALWAYS"""  # noqa: E501
                )

            # validate notification time
            if values.get("notification"):
                if values.get("notification").notifications:
                    for notification in values.get(
                        "notification"
                    ).notifications:
                        if (
                            notification.trigger_type
                            == NotificationTriggerType.FIXED
                            and not (
                                values.get("start_time")
                                < notification.at_time
                                < values.get("end_time")  # noqa: E501
                            )
                        ):
                            raise ValueError(
                                """Activity/flow is unavailable at this time"""  # noqa: E501
                            )

                        if (
                            notification.trigger_type
                            == NotificationTriggerType.RANDOM
                            and not (
                                values.get("start_time")
                                < notification.from_time
                                < notification.to_time
                                < values.get("end_time")  # noqa: E501
                            )
                        ):
                            raise ValueError(
                                """Activity/flow is unavailable at this time"""  # noqa: E501
                            )
                if values.get("notification").reminder:
                    if not (
                        values.get("start_time")
                        < values.get("notification").reminder.reminder_time
                        < values.get("end_time")
                    ):
                        raise ValueError(
                            """Activity/flow is unavailable at this time"""
                        )
        return values
