import uuid

from apps.shared.enums import Language
from apps.shared.errors import (
    BaseError,
    ValidationError
)
from apps.shared.exception import NotFoundError, AccessDeniedError


class EventNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No such event with {key}={value}."
    }


class PeriodicityNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No such periodicity with {key}={value}."
    }


class AppletScheduleNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No schedules found for applet {applet_id}"
    }


class AccessDeniedToApplet(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied to applet."
    }


class ActivityOrFlowNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Activity/Flow not found."
    }


class ScheduleNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Schedule not found."
    }


class EventAlwaysAvailableExistsError(ValidationError):
    messages = {
        Language.ENGLISH: "'AlwaysAvailable' event already exists."
    }


class EventError(BaseError):
    def __init__(self, message: str = "Event service error") -> None:
        super().__init__(message=message)


class UserEventAlreadyExists(ValidationError):
    def __init__(self, user_id: uuid.UUID, event_id: uuid.UUID) -> None:
        super().__init__(
            message=f"The event {event_id} for user {user_id} already exists."
        )


class ActivityEventAlreadyExists(ValidationError):
    def __init__(self, activity_id: uuid.UUID, event_id: uuid.UUID) -> None:
        msg = (
            f"The event {event_id} for activity {activity_id} already exists."
        )
        super().__init__(message=msg)


class FlowEventAlreadyExists(ValidationError):
    def __init__(self, flow_id: uuid.UUID, event_id: uuid.UUID) -> None:
        super().__init__(
            message=f"The event {event_id} for flow {flow_id} already exists."
        )
