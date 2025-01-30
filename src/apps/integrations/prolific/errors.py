from gettext import gettext as _

from apps.shared.exception import UnauthorizedError, ValidationError


class ProlificInvalidApiTokenError(UnauthorizedError):
    message = _("Prolific token is invalid.")


class ProlificInvalidStudyError(UnauthorizedError):
    message = _("Invalid Prolific study id.")


class ProlificIntegrationNotConfiguredError(ValidationError):
    message = _("Prolific integration not configured.")
