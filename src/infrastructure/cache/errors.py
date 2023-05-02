from apps.shared.exception import NotFoundError
from gettext import gettext as _


class CacheNotFound(NotFoundError):
    message = _("Can not find item in the cache.")
