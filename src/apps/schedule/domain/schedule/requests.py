import uuid

from pydantic import Field, root_validator, validator

from apps.schedule.domain.constants import NotificationTriggerType, PeriodicityType
from apps.schedule.domain.schedule.base import BaseEvent, BaseNotificationSetting, BasePeriodicity, BaseReminderSetting
from apps.schedule.errors import (
    ActivityOrFlowRequiredError,
    OneTimeCompletionCaseError,
    StartEndTimeAccessBeforeScheduleCaseError,
    StartEndTimeEqualError,
    UnavailableActivityOrFlowError,
)
from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "EventRequest",
    "PeriodicityRequest",
    "NotificationSettingRequest",
    "ReminderSettingRequest",
    "EventUpdateRequest",
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

    @validator("notifications")
    def validate_notification_order(cls, value):
        if value:
            # set order of notifications
            for i, notification in enumerate(value):
                notification.order = i + 1
        return value


class EventUpdateRequest(BaseEvent, InternalModel):
    periodicity: PeriodicityRequest
    notification: Notification | None = None

    @root_validator
    def validate_optional_fields(cls, values):
        # if periodicity is Always, one_time_completion must be set.
        if values.get("periodicity").type == PeriodicityType.ALWAYS and not isinstance(
            values.get("one_time_completion"), bool
        ):
            raise OneTimeCompletionCaseError()

        # if periodicity is not Always, start_time and end_time, access_before_schedule must be set. # noqa: E501
        if values.get("periodicity").type != PeriodicityType.ALWAYS:
            if (
                not bool(values.get("start_time"))
                or not bool(values.get("end_time"))
                or not isinstance(values.get("access_before_schedule"), bool)
            ):
                raise StartEndTimeAccessBeforeScheduleCaseError()

            # validate notification time
            if values.get("notification"):
                if values.get("notification").notifications:
                    for notification in values.get("notification").notifications:
                        if notification.trigger_type == NotificationTriggerType.FIXED and (
                            values.get("start_time") is None
                            or values.get("end_time") is None
                            or notification.at_time is None  # noqa: E501
                        ):
                            raise UnavailableActivityOrFlowError()

                        if notification.trigger_type == NotificationTriggerType.RANDOM and (
                            values.get("start_time") is None
                            or values.get("end_time") is None
                            or notification.from_time is None
                            or notification.to_time is None  # noqa: E501
                        ):
                            raise UnavailableActivityOrFlowError()
                if values.get("notification").reminder:
                    if (
                        values.get("start_time") is None
                        or values.get("end_time") is None
                        or values.get("notification").reminder.reminder_time is None
                    ):
                        raise UnavailableActivityOrFlowError()

        if values.get("start_time") == values.get("end_time"):
            raise StartEndTimeEqualError()

        return values


class EventRequest(EventUpdateRequest):
    respondent_id: uuid.UUID | None
    activity_id: uuid.UUID | None = Field(
        None,
        description="If flow_id is not set, activity_id must be set.",
    )
    flow_id: uuid.UUID | None = Field(
        None,
        description="If activity_id is not set, flow_id must be set.",
    )

    @root_validator
    def validate_optional_fields_activity_or_flow(cls, values):
        if not (bool(values.get("activity_id")) ^ bool(values.get("flow_id"))):
            raise ActivityOrFlowRequiredError()

        return values
