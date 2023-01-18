from apps.shared.errors import BaseError


class NotificationLogError(BaseError):
    def __init__(
        self, message: str = "Unexpected NotificationLog error"
    ) -> None:
        super().__init__(message=message)
