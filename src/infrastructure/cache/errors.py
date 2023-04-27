from apps.shared.enums import Language
from apps.shared.exception import NotFoundError


class CacheNotFound(NotFoundError):
    messages = {
        Language.ENGLISH: "Can not find item {key} in the cache"
    }
