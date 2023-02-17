from apps.shared.errors import BaseError, NotFoundError, ValidationError

__all__ = [
    "AppletsError",
    "AppletAlreadyExist",
    "AppletNotFoundError",
    "UserAppletAccessesNotFound",
    "AppletAccessDenied",
    "AppletsFolderAccessDenied",
    "AppletLinkNotFoundError",
    "AppletLinkAlreadyExist",
]


class AppletsError(BaseError):
    def __init__(self, *_, message="Applets service error.") -> None:
        super().__init__(message=message)


class AppletAlreadyExist(ValidationError):
    def __init__(self, *_, message="Applet already exist.") -> None:
        super().__init__(message=message)


class AppletNotFoundError(NotFoundError):
    def __init__(self, *_, key: str, value: str) -> None:
        super().__init__(message=f"No such applets with {key}={value}.")


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, *_, id_: int) -> None:
        super().__init__(message=f"No such UserAppletAccess with id={id_}.")


class AppletAccessDenied(ValidationError):
    def __init__(self, *_, message="Access denied to applet.") -> None:
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
