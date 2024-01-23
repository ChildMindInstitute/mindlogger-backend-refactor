from gettext import gettext as _

from apps.shared.exception import NotFoundError, ValidationError


class AppletNameExistsError(ValidationError):
    message = _("This Applet name is already taken in the Library.")


class AppletVersionExistsError(ValidationError):
    message = _("This Applet version already exists in the Library.")


class LibraryItemDoesNotExistError(NotFoundError):
    message = _("This Library Item does not exists.")


class AppletVersionDoesNotExistError(NotFoundError):
    message = _("This Applet version is not shared to the library.")
