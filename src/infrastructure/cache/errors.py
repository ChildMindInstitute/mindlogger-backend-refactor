from apps.shared.errors import NotFoundError


class CacheNotFound(NotFoundError):
    def __init__(self, key: str) -> None:
        message = f"Can not find item {key} in the cache"
        super().__init__(message)
