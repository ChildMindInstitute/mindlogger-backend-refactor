from gettext import gettext as _

from apps.shared.exception import InternalServerError


class NotificationLogError(InternalServerError):
    message = _("Unexpected NotificationLog error.")
