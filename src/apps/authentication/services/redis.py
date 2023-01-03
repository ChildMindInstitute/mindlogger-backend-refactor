import datetime
import json

from apps.authentication.domain.token import InternalToken, TokenInfo
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from infrastructure.cache import BaseCacheService
from infrastructure.cache.domain import CacheEntry
from infrastructure.cache.errors import CacheNotFound


class TokensCache(BaseCacheService[TokenInfo]):
    """The concrete class that realized tokens cache engine.
    In order to be able to save multiple tokens for a single user
    the specific key builder is used.

    The example of a key:
        __classname__:tokens-blacklist:john@email.com:access_token:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
        eyJzdWIiOiI1IiwiZXhwIjoxNjcyNzQ1ODIxfQ.
        inB6EtnmyCx7x1GATrsiNSLp1ikHUop4jgx4uXTVxgY

    __classname__ -- is taken from the parent class key builder
    tokens-blacklist -- blacklist identifier
    john@email.com -- user's email
    access_token -- purpose of the token
    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
    eyJzdWIiOiI1IiwiZXhwIjoxNjcyNzQ1ODIxfQ.
    inB6EtnmyCx7x1GATrsiNSLp1ikHUop4jgx4uXTVxgY -- token body

    This strategy is taken in order to create unique pairs
    that consist of "tokens-blacklist", user's email,
    purpose of the token - for example "access_token"
    and token body.
    """

    def build_key(self, email: str, token_purpose: str, raw_token: str) -> str:
        """Returns a key with the additional namespace for this cache."""

        return f"tokens-blacklist:{email}:{token_purpose}:{raw_token}"

    async def get(
        self,
        email: str,
        token_purpose: str,
        raw_token: str,
    ) -> CacheEntry[TokenInfo]:
        cache_record: dict = await self._get(
            self.build_key(email, token_purpose, raw_token)
        )

        return CacheEntry[TokenInfo](**cache_record)

    # async def delete(self, email: str, key: uuid.UUID | str) -> None:
    #     _key = self.build_key(email, key)
    #     await self._delete(_key)

    async def all(self, email: str) -> list[CacheEntry[TokenInfo]]:
        # Create a key to fetch all records for
        # the specific email prefix in a cache key
        key = f"tokens-blacklist:{email}:*"

        # Fetch keys for retrieving
        if not (keys := await self.redis_client.keys(self._build_key(key))):
            raise CacheNotFound(f"There is no Tokens for {email}")

        results: list[bytes] = await self.redis_client.mget(keys)

        return [
            CacheEntry[TokenInfo](**json.loads(result)) for result in results
        ]


class TokensService:
    def __init__(
        self,
    ):
        self._cache: TokensCache = TokensCache()

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
            # Create internal TokenInfo object
            token_purpose = "access_token"
            user: User = await UsersCRUD().get_by_id(schema.payload.sub)
            token_info = TokenInfo(
                email=user.email,
                token_purpose=token_purpose,
                raw_token=schema.raw_token,
                user_id=schema.payload.sub,
            )

            # Build the cache key that consist of
            # identifier - "tokens-blacklist",
            # email, token_purpose - "access_token", raw_token.
            key: str = self._cache.build_key(
                user.email, token_purpose, schema.raw_token
            )

            # Save token to the cache blacklist
            _: CacheEntry[TokenInfo] = await self._cache.set(
                key=key,
                instance=token_info,
                ttl=ttl,
            )
