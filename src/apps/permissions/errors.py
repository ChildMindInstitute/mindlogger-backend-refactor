from apps.shared.domain.base import BaseError


class UserAppletAccessesError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Permissions service error"
        super().__init__(message or fallback, *args)
