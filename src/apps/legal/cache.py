import uuid

from apps.legal.constants import MSA_TEST_SETTINGS_TTL_SECONDS
from apps.legal.domain import MsaTestSettings
from infrastructure.cache import BaseCacheService
from infrastructure.cache.domain import CacheEntry

__all__ = ["MsaTestSettingsCache"]


class MsaTestSettingsCache(BaseCacheService[MsaTestSettings]):
    """Each user's own MSA test settings, keyed by user id: MsaTestSettingsCache:<user id>"""

    async def get(self, user_id: uuid.UUID) -> CacheEntry[MsaTestSettings]:
        cache_record: dict = await self._get(str(user_id))
        return CacheEntry[MsaTestSettings](**cache_record)

    async def save(self, user_id: uuid.UUID, values: MsaTestSettings) -> CacheEntry[MsaTestSettings]:
        return await self.set(str(user_id), values, ttl=MSA_TEST_SETTINGS_TTL_SECONDS)

    async def delete(self, user_id: uuid.UUID) -> None:
        await self._delete(str(user_id))
