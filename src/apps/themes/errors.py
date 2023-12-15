from gettext import gettext as _

from apps.shared.exception import (
    InternalServerError,
    NotFoundError,
    ValidationError,
)


class ThemeNotFoundError(NotFoundError):
    message_is_template: bool = True
    message = _("No such theme with {key}={value}.")


class ThemesError(InternalServerError):
    message = _("Themes service error.")


class ThemeAlreadyExist(ValidationError):
    message = _("Theme already exist.")
