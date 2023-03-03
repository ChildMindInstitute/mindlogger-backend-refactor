from apps.shared.errors import BaseError, ValidationError

__all__ = [
    "UserAppletAccessesNotFound",
    "AppletAccessDenied",
]


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, *_, id_: int) -> None:
        super().__init__(message=f"No such UserAppletAccess with id={id_}.")


class AppletAccessDenied(ValidationError):
    def __init__(self, *_, message="Access denied to applet.") -> None:
        super().__init__(message=message)
