from gettext import gettext as _

from apps.shared.exception import ValidationError


class UniqueIntegrationError(ValidationError):
    message = _("Integrations must be unique.")
