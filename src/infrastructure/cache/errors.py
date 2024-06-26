from gettext import gettext as _

from apps.shared.exception import NotFoundError


class CacheNotFound(NotFoundError):
    message = _("Can not find item in the cache.")


class PasswordRecoveryHealthCheckNotValid(CacheNotFound):
    message = _("Invalid or Expired Link.")
