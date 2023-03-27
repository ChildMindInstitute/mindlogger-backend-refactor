import datetime

from apps.authentication.domain.token import (
    InternalToken,
    TokenInfo,
    TokenPurpose,
)
from apps.authentication.services.cache import TokensBlacklistCache
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from infrastructure.cache.domain import CacheEntry

__all__ = ["TokensService"]


class TokensService:
    def __init__(self, session) -> None:
        self._cache: TokensBlacklistCache = TokensBlacklistCache()
        self.session = session

    async def fetch_all(self, email: str) -> list[TokenInfo]:
        cache_entries: list[CacheEntry[TokenInfo]] = await self._cache.all(
            email=email
        )

        return [entry.instance for entry in cache_entries]

    async def add_access_token_to_blacklist(
        self, schema: InternalToken
    ) -> None:
        now = datetime.datetime.now()
        ttl = schema.payload.exp - int(now.timestamp())

        if ttl > 1:
            user: User = await UsersCRUD(self.session).get_by_id(
                schema.payload.sub
            )

            token_info = TokenInfo(
                email=user.email,
                token_purpose=TokenPurpose.ACCESS,
                raw_token=schema.raw_token,
                user_id=schema.payload.sub,
            )

            # Build the cache key
            key: str = self._cache.build_key(
                user.email, TokenPurpose.ACCESS, schema.raw_token
            )

            # Save token to the cache blacklist
            _: CacheEntry[TokenInfo] = await self._cache.set(
                key=key,
                instance=token_info,
                ttl=ttl,
            )
