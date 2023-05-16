__all__ = [
    "FolderAlreadyExist",
    "FolderDoesNotExist",
    "FolderIsNotEmpty",
    "FolderAccessDenied",
    "AppletNotInFolder",
]

from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, ValidationError


class FolderAccessDenied(AccessDeniedError):
    message = _("Access denied.")


class FolderAlreadyExist(ValidationError):
    message = _("Folder already exists.")


class FolderDoesNotExist(ValidationError):
    message = _("Folder does not exist.")


class FolderIsNotEmpty(ValidationError):
    message = _("Folder has applets, move applets from folder to delete it.")


class AppletNotInFolder(ValidationError):
    message = _("Applet not in folder.")
