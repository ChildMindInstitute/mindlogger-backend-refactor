import datetime
import uuid

import pytest

from apps.legal.cache import MsaTestSettingsCache
from apps.legal.domain import MsaTestSettings
from infrastructure.cache import CacheNotFound


async def test_msa_test_settings_cache_round_trip():
    user_id = uuid.uuid4()
    values = MsaTestSettings(msa_version="test-1", effective_from=datetime.date(2026, 8, 1), grace_days=60)
    cache = MsaTestSettingsCache()

    await cache.save(user_id, values)
    assert (await cache.get(user_id)).instance == values

    await cache.delete(user_id)
    with pytest.raises(CacheNotFound):
        await cache.get(user_id)
