from apps.shared.enums import Language
from apps.shared.errors import (
    BaseError,
    ValidationError,
)

__all__ = [
    "AppletsError",
    "AppletAlreadyExist",
    "AppletNotFoundError",
    "AppletsFolderAccessDenied",
    "AppletLinkNotFoundError",
    "AppletLinkAlreadyExist",
    "InvalidVersionError",
    "AppletPasswordValidationError",
]

from apps.shared.exception import NotFoundError, AccessDeniedError


class AppletNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No such applets with {key}={value}."
    }


class AppletVersionNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Applet version not found."
    }


class NotValidAppletHistory(NotFoundError):
    messages = {
        Language.ENGLISH: "Not valid applet version."
    }


class AppletLinkNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "No such applet link for id={applet_id}."
    }


class AccessLinkDoesNotExistError(NotFoundError):
    messages = {
        Language.ENGLISH: "Access link does not exist."
    }


class AppletsFolderAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied to folder."
    }


class AppletsError(BaseError):
    def __init__(self, *_, message="Applets service error.") -> None:
        super().__init__(message=message)


class AppletAlreadyExist(ValidationError):
    def __init__(self, *_, message="Applet already exists.") -> None:
        super().__init__(message=message)


class AppletLinkAlreadyExist(ValidationError):
    def __init__(self, *_, message="Applet link already exists.") -> None:
        super().__init__(message=message)


class AppletPasswordValidationError(ValidationError):
    def __init__(self, *_, message="Applet password does not match.") -> None:
        super().__init__(message=message)


class InvalidVersionError(ValidationError):
    def __init__(self, *_, message="Invalid version.") -> None:
        super().__init__(message=message)
