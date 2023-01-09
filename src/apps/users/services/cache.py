import json
import uuid

from apps.users.domain import PasswordRecoveryInfo
from infrastructure.cache import BaseCacheService, CacheNotFound
from infrastructure.cache.domain import CacheEntry

__all__ = ["PasswordRecoveryCache"]


class PasswordRecoveryCache(BaseCacheService[PasswordRecoveryInfo]):
    """The concrete class that realized password recovery cache engine.
    The specific key builder is used.

    The example of a key:
        __class__.__name__:john@email.com:fe46c05a-1790-4b...

    This strategy is taken in order to create unique pairs
    that consist of a namespace, user's email
    and key - uuid.
    """

    def build_key(self, email: str, key: uuid.UUID | str) -> str:
        """Returns a key with the additional namespace for this cache."""

        return f"{email}:{key}"

    async def get(
        self,
        email: str,
        key: uuid.UUID | str,
    ) -> CacheEntry[PasswordRecoveryInfo]:
        cache_record: dict = await self._get(self.build_key(email, key))

        return CacheEntry[PasswordRecoveryInfo](**cache_record)

    async def delete(self, email: str, key: uuid.UUID | str):
        await self._delete(self.build_key(email, key))

    async def all(self, email: str) -> list[CacheEntry[PasswordRecoveryInfo]]:
        # Create a key to fetch all records for
        # the specific email prefix in a cache key
        key = f"{email}:*"

        # Fetch keys for retrieving
        if not (keys := await self.redis_client.keys(self._build_key(key))):
            raise CacheNotFound(f"There is no password recovery for {email}")

        results: list[bytes] = await self.redis_client.mget(keys)

        return [
            CacheEntry[PasswordRecoveryInfo](**json.loads(result))
            for result in results
        ]

    async def delete_all_entries(self, email: str):
        try:
            cache_entries: list[
                CacheEntry[PasswordRecoveryInfo]
            ] = await self.all(email=email)
        except CacheNotFound:
            raise
        for cache_entry in cache_entries:
            await self.delete(
                email=cache_entry.instance.email, key=cache_entry.instance.key
            )
