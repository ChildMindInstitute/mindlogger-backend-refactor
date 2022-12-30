from apps.shared.errors import BaseError, ValidationError


class NotificationLogError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "NotificationLog service error"
        super().__init__(message or fallback, *args)


class NotificationLogAlreadyExist(ValidationError):
    def __init__(self, *args) -> None:
        message = "Notification Log already exist"
        super().__init__(message, *args)
