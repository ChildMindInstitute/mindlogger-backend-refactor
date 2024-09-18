import datetime
import json
import re
import typing

import redis.asyncio as redis
from redis.typing import EncodableT
from sentry_sdk import capture_exception

from config import settings


class RedisCacheTest:
    _storage: dict = {}

    async def get(self, key: str):
        now = datetime.datetime.utcnow()
        value, expiry = self._storage.get(key, [None, None])

        if not value or (expiry and now > expiry):
            return None

        return value

    async def set(self, name, value, ex=None, **kwargs):
        now = datetime.datetime.utcnow()
        self._storage[name] = [
            value,
            (now + datetime.timedelta(seconds=ex)) if ex else None,
        ]
        return True

    async def delete(self, key: str) -> bool:
        self._storage.pop(key)
        return True

    async def keys(self, pattern: str = "*") -> list[str]:
        if pattern == "*":
            pattern = ".+"
        filtered_keys = []
        for key, [_, expire] in self._storage.items():
            if expire and expire < datetime.datetime.utcnow():
                continue
            is_match = re.match(pattern, key)
            if is_match:
                filtered_keys.append(key)
        return filtered_keys

    async def mget(self, keys) -> list[typing.Any]:
        results = []
        for key in keys:
            result, expire = self._storage.get(key, [None, None])
            if expire > datetime.datetime.utcnow():
                results.append(result)
        return results

    async def publish(self, channel: str, value: dict):
        values, expiry = self._storage.get(channel, ([], None))
        values.append(json.dumps(value, default=str))
        self._storage[channel] = (values, expiry)

    async def messages(self, channel_name: str):
        values, expiry = self._storage.get(channel_name, ([], None))
        for value in values:
            yield value


class RedisCache:
    """Singleton Redis cache client"""

    _initialized: bool = False
    _instance = None
    configuration: dict = {}
    _cache: typing.Optional[redis.Redis] = None
    host: str
    port: int
    db: int
    expire_duration: typing.Optional[int] = None
    env: str | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if self._initialized:
            return

        self.configuration = dict()
        self.env = settings.env
        self.host = settings.redis.host
        self.port = settings.redis.port
        self.db = settings.redis.db
        self.expire_duration = settings.redis.default_ttl

        for key, val in kwargs.items():
            self.configuration[key.lower()] = val

        self._start()

        self._initialized = True

    def _start(self):
        if self.env == "testing":
            self._cache = RedisCacheTest()
            return
        if not self.host:
            return
        try:
            self._cache = redis.client.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                **self.configuration,
            )
        except redis.exceptions.ConnectionError as e:
            try:
                capture_exception(e)
            except ImportError:
                print(e)

    async def get(self, key: str) -> typing.Optional[str]:
        if not self._cache:
            return None
        try:
            value = await self._cache.get(key)
            return value
        except redis.RedisError:
            return None

    async def set(self, key: str, value: EncodableT, ex=None) -> bool:
        if not self._cache:
            return False
        if not ex:
            ex = self.expire_duration
        result = await self._cache.set(key, value, ex=ex)
        return result

    async def delete(self, key) -> bool:
        if not self._cache:
            return False
        await self._cache.delete(key)
        return True

    async def keys(self, key: str = "*") -> list[str]:
        if not self._cache:
            return []
        return await self._cache.keys(key)

    async def mget(self, keys: list[str]) -> list[typing.Any]:
        if not self._cache:
            return []
        return await self._cache.mget(keys)

    async def publish(self, channel: str, value: dict):
        assert self._cache
        await self._cache.publish(channel, json.dumps(value, default=str))

    async def messages(self, channel_name: str):
        assert self._cache
        pubsub = self._cache.pubsub()
        await pubsub.subscribe(channel_name)
        async for message in pubsub.listen():
            yield message
