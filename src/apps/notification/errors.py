from apps.shared.errors import BaseError


class NotificationLogError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "NotificationLog service error"
        super().__init__(message or fallback, *args)
