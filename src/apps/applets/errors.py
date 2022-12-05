from apps.shared.domain import BaseError


class AppletsError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Applets service error"
        super().__init__(message or fallback, *args)


class AppletsNotFoundError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Applets service error"
        super().__init__(message or fallback, *args)
