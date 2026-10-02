from gettext import gettext as _

from apps.shared.exception import ValidationError


class MSAVersionOutdatedError(ValidationError):
    message = _("The Master Services Agreement has been updated. Please review it and try again.")
    error_code = "LEGAL.MSA_VERSION_OUTDATED"
