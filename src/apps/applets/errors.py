from gettext import gettext as _

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

from apps.shared.exception import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)


class AppletNotFoundError(NotFoundError):
    message = _("No such applets with {key}={value}.")


class AppletVersionNotFoundError(NotFoundError):
    message = _("Applet version not found.")


class NotValidAppletHistory(NotFoundError):
    message = _("Not valid applet version.")


class AppletLinkNotFoundError(NotFoundError):
    message = _("No such applet link for id={applet_id}.")


class AccessLinkDoesNotExistError(NotFoundError):
    message = _("Access link does not exist.")


class AppletsFolderAccessDenied(AccessDeniedError):
    message = _("Access denied to folder.")


class AppletsError(ValidationError):
    message = _("Can not make the looking up applets by {key} {value}.")


class AppletAlreadyExist(ValidationError):
    message = _("Applet already exists.")


class AppletLinkAlreadyExist(ValidationError):
    message = _("Applet link already exists.")


class AppletPasswordValidationError(ValidationError):
    message = _("Applet password does not match.")


class InvalidVersionError(ValidationError):
    message = _("Invalid version.")
