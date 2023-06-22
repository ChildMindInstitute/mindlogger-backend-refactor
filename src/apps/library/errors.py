from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, NotFoundError

__all__ = [
    "AppletNameExistsError",
    "AppletVersionExistsError",
    "LibraryItemDoesNotExistError",
]


class AppletNameExistsError(AccessDeniedError):
    message = _("This Applet name is already taken in the Library.")


class AppletVersionExistsError(AccessDeniedError):
    message = _("This Applet version is already exists in the Library.")


class LibraryItemDoesNotExistError(NotFoundError):
    message = _("This Library Item does not exists.")
