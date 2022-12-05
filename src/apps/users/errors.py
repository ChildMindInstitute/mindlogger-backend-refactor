from apps.shared.domain import BaseError


class UsersError(BaseError):
    pass


class UserNotFound(BaseError):
    pass


class UserAppletAccessesError(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Permissions service error"
        super().__init__(message or fallback, *args)


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Permissions service error"
        super().__init__(message or fallback, *args)
