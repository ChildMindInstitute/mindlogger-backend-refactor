from apps.shared.errors import NotFoundError


class CacheNotFound(NotFoundError):
    def __init__(self, key: str) -> None:
        super().__init__(message=f"Can not find item {key} in the cache")
