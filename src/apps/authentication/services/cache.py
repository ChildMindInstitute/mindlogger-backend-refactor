import json

from apps.authentication.domain.token import TokenInfo, TokenPurpose
from infrastructure.cache import BaseCacheService
from infrastructure.cache.domain import CacheEntry
from infrastructure.cache.errors import CacheNotFound

__all__ = ["TokensBlacklistCache"]


class TokensBlacklistCache(BaseCacheService[TokenInfo]):
    """The concrete class that realized tokens cache engine.
    In order to be able to save multiple tokens for a single user
    the specific key builder is used.

    The example of a key:
        __class__.__name__:john@email.com:access:eyJhbGciOiJIUzI1NiIs...
        __class__.__name__:john@email.com:refresh:UyQpbGcpsiJIUzI1NiIs...

    This strategy is taken in order to create unique pairs
    that consist of a namespace, user's email,
    purpose of the token - for example "access_token"
    and token body.
    """

    def build_key(self, email: str, token_purpose: TokenPurpose, raw_token: str) -> str:
        """Returns a key with the additional namespace for this cache."""

        return f"{email}:{token_purpose}:{raw_token}"

    async def get(
        self,
        email: str,
        token_purpose: TokenPurpose,
        raw_token: str,
    ) -> CacheEntry[TokenInfo]:
        cache_record: dict = await self._get(self.build_key(email, token_purpose, raw_token))

        return CacheEntry[TokenInfo](**cache_record)

    async def all(self, email: str) -> list[CacheEntry[TokenInfo]]:
        # Create a key to fetch all records for
        # the specific email prefix in a cache key
        key = f"{email}:*"

        # Fetch keys for retrieving
        if not (keys := await self.redis_client.keys(self._build_key(key))):
            raise CacheNotFound()

        results: list[bytes] = await self.redis_client.mget(keys)

        return [CacheEntry[TokenInfo](**json.loads(result)) for result in results]

    # TODO: Clarify how to deal with
    #       removing token / adding token to the blacklist
    # async def delete(self, email: str, key: uuid.UUID | str) -> None:
    #     _key = self.build_key(email, key)
    #     await self._delete(_key)
