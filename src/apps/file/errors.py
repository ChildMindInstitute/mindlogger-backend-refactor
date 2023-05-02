from apps.shared.exception import NotFoundError
from gettext import gettext as _


class FileNotFoundError(NotFoundError):
    message = _("File not found.")
