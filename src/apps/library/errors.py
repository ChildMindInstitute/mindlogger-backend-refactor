from gettext import gettext as _

from apps.shared.exception import AccessDeniedError

__all__ = [
    "AppletNameExistsError",
]


class AppletNameExistsError(AccessDeniedError):
    message = _("This Applet name is already taken in the Library.")
