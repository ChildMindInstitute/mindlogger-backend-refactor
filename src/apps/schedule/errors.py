from apps.shared.errors import BaseError, NotFoundError, ValidationError


class EventError(BaseError):
    def __init__(self, message: str = "Event service error") -> None:
        super().__init__(message=message)


class UserEventAlreadyExists(ValidationError):
    def __init__(self, user_id: int, event_id: int) -> None:
        super().__init__(
            message=f"The event {event_id} for user {user_id} already exists."
        )


class ActivityEventAlreadyExists(ValidationError):
    def __init__(self, activity_id: int, event_id: int) -> None:
        super().__init__(
            message=f"The event {event_id} for activity {activity_id} already exists."
        )


class FlowEventAlreadyExists(ValidationError):
    def __init__(self, flow_id: int, event_id: int) -> None:
        super().__init__(
            message=f"The event {event_id} for flow {flow_id} already exists."
        )


class EventNotFoundError(NotFoundError):
    def __init__(self, key: str, value: str) -> None:
        super().__init__(message=f"No such event with {key}={value}.")
