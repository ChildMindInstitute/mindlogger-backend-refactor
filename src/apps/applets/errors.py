from apps.shared.errors import BaseError, NotFoundError, ValidationError

__all__ = [
    "AppletsError",
    "AppletAlreadyExist",
    "AppletNotFoundError",
    "AppletsFolderAccessDenied",
    "AppletLinkNotFoundError",
    "AppletLinkAlreadyExist",
    "AppletPasswordValidationError",
]


class AppletsError(BaseError):
    def __init__(self, *_, message="Applets service error.") -> None:
        super().__init__(message=message)


class AppletAlreadyExist(ValidationError):
    def __init__(self, *_, message="Applet already exists.") -> None:
        super().__init__(message=message)


class AppletNotFoundError(NotFoundError):
    def __init__(self, *_, key: str, value: str) -> None:
        super().__init__(message=f"No such applets with {key}={value}.")


class NotValidAppletHistory(NotFoundError):
    def __init__(self, *_, message="Not valid applet version.") -> None:
        super().__init__(message=message)


class AppletsFolderAccessDenied(ValidationError):
    def __init__(self, *_, message="Access denied to folder.") -> None:
        super().__init__(message=message)


class AppletLinkNotFoundError(NotFoundError):
    def __init__(self, *_, applet_id: str) -> None:
        super().__init__(message=f"No such applet link for id={applet_id}.")


class AppletLinkAlreadyExist(ValidationError):
    def __init__(self, *_, message="Applet link already exists.") -> None:
        super().__init__(message=message)


class AppletPasswordValidationError(ValidationError):
    def __init__(self, *_, message="Applet password does not match.") -> None:
        super().__init__(message=message)
