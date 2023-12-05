from gettext import gettext as _

from apps.shared.exception import (
    InternalServerError,
    NotFoundError,
    ValidationError,
)


class LorisServerError(ValidationError):
    message = _("Loris server error {message}.")


class ConsentNotFoundError(NotFoundError):
    message = _("No such consent with {key}={value}.")


class ConsentError(InternalServerError):
    message = _("Consent service error.")
