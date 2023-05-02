from apps.shared.exception import InternalServerError
from gettext import gettext as _


class NotificationLogError(InternalServerError):
    message = _("Unexpected NotificationLog error")
