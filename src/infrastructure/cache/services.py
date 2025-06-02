import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Generic

from config import settings
from infrastructure.cache.domain import CacheEntry
from infrastructure.cache.errors import CacheNotFound
from infrastructure.cache.types import _InputObject

__all__ = ["BaseCacheService"]

from infrastructure.utility.redis_client import RedisCache


class BaseCacheService(ABC, Generic[_InputObject]):
    """The base cache abstract class.

    The example of the subclass usage:

        [In 0]: john = User(...)

        [In 1]: class UsersCache(BaseCacheService[Invitation]):
                    async def get(self, id_: int) -> CacheEntry[Invitation]:
                        cache_entry: dict = await self._get(id_)
                        return CacheEntry[User](**cache_entry)

        [In 2]: cache_entry: CacheEntry[User] = UsersCache().set(id_, john)
        [In 3]: cache_entry: CacheEntry[User] = UsersCache().get(id_)

    NOTE: The example of a cache record key: `UsersCache:13`
          where UsersCache is __class__.__name__ and 13 is a user's id
    """

    def __init__(self):
        self.redis_client = self.__get_redis_client()
        self.default_ttl = settings.redis.default_ttl

    @staticmethod
    def __get_redis_client():
        """Returns an instance of redis client.

        Instance is created only once and then the same instance is returned
        """

        reference = "_redis_client_instance"

        try:
            return getattr(BaseCacheService, reference)
        except AttributeError:
            redis_client = RedisCache()
            setattr(BaseCacheService, reference, redis_client)
            return redis_client

    def _build_key(self, key: str) -> str:
        """Returns a key with the additional namespace for this cache.

        Example of usage:
            [In 1]:  _build_key("john@email.com")
            [Out 1]: ConcreteCache:john@email.com

        """

        return f"{self.__class__.__name__}:{key}"

    async def _get(self, key: str) -> dict:
        if result := await self.redis_client.get(self._build_key(key)):
            return json.loads(result)

        raise CacheNotFound()

    @abstractmethod
    async def get(self, *args, **kwargs) -> CacheEntry[_InputObject]:
        """Returns an instance by the key from the cache.
        This method is abstract in order to provide better
        type annotations experience.
        """

        pass

    async def set(
        self,
        key: str,
        instance: _InputObject,
        ttl: int | None = None,
    ) -> CacheEntry[_InputObject]:
        enhanced_cache_entry: CacheEntry[_InputObject] = CacheEntry(
            instance=instance,
            created_at=datetime.now(timezone.utc),
        )

        await self.redis_client.set(
            key=self._build_key(key=key),
            value=enhanced_cache_entry.json(),
            ex=(ttl or self.default_ttl),
        )

        # Return another rich data model after saving into the cache
        return enhanced_cache_entry

    async def _delete(self, key: str) -> None:
        await self.redis_client.delete(self._build_key(key))
