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
    "Notification",
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
            for i, notification in enumerate(value, start=1):
                notification.order = i
        return value


class EventUpdateRequest(BaseEvent, InternalModel):
    periodicity: PeriodicityRequest
    notification: Notification | None = None

    @root_validator
    def validate_optional_fields(cls, values):  # noqa: C901
        # if periodicity is Always, one_time_completion must be set.
        if values.get("periodicity").type == PeriodicityType.ALWAYS and not isinstance(
            values.get("one_time_completion"), bool
        ):
            raise OneTimeCompletionCaseError()

        start_time = values.get("start_time")
        end_time = values.get("end_time")
        # if periodicity is not Always, start_time and end_time, access_before_schedule must be set
        if values.get("periodicity").type != PeriodicityType.ALWAYS:
            if not start_time or not end_time or not isinstance(values.get("access_before_schedule"), bool):
                raise StartEndTimeAccessBeforeScheduleCaseError()

            # validate notification time
            if values.get("notification"):
                if values.get("notification").notifications:
                    for notification in values.get("notification").notifications:
                        # keep same logic if the event is not cross-day
                        if start_time < end_time:
                            if notification.trigger_type == NotificationTriggerType.FIXED and (
                                notification.at_time < start_time or notification.at_time > end_time
                            ):
                                raise UnavailableActivityOrFlowError()

                            if notification.trigger_type == NotificationTriggerType.RANDOM and (
                                notification.from_time < start_time
                                or notification.from_time > end_time
                                or notification.to_time < start_time
                                or notification.to_time > end_time
                            ):
                                raise UnavailableActivityOrFlowError()
                        # logic for cross-day events
                        else:
                            if notification.trigger_type == NotificationTriggerType.FIXED and (
                                notification.at_time < start_time and notification.at_time > end_time
                            ):
                                raise UnavailableActivityOrFlowError()

                            if notification.trigger_type == NotificationTriggerType.RANDOM and (
                                (notification.from_time < start_time and notification.from_time > end_time)
                                or (notification.to_time < start_time and notification.to_time > end_time)
                            ):
                                raise UnavailableActivityOrFlowError()

                if values.get("notification").reminder:
                    reminder = values.get("notification").reminder
                    # keep same logic if the event is not cross-day
                    if start_time < end_time:
                        if reminder.reminder_time < start_time or reminder.reminder_time > end_time:
                            raise UnavailableActivityOrFlowError()
                    else:
                        if reminder.reminder_time < start_time and reminder.reminder_time > end_time:
                            raise UnavailableActivityOrFlowError()

        if start_time == end_time:
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
