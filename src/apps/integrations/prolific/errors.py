from gettext import gettext as _

from apps.shared.exception import UnauthorizedError

class ProlificInvalidApiTokenError(UnauthorizedError):
    message = _("Prolific token is invalid.")