from gettext import gettext as _

from apps.shared.exception import NotFoundError


class FileNotFoundError(NotFoundError):
    message = _("File not found.")
