import datetime
import typing

import aioredis
from sentry_sdk import capture_exception

from config import settings


class _Cache:
    _storage: dict = {}

    async def get(self, key: str):
        now = datetime.datetime.now()
        value, expiry = self._storage.get(key, [None, None])
        if not value:
            return None
        if expiry and now > expiry:
            return None
        return value

    async def set(self, name, value, ex=None, **kwargs):
        now = datetime.datetime.now()
        self._storage[name] = [
            value,
            (now + datetime.timedelta(seconds=ex)) if ex else None,
        ]
        return True


class RedisCache:
    """Singleton Redis cache client"""

    _initialized: bool = False
    _instance: None = None
    configuration: dict = {}
    _cache: typing.Optional[aioredis.Redis] = None
    host: typing.Optional[str] = None
    port: typing.Optional[str] = None
    db: typing.Optional[str] = None
    expire_duration: typing.Optional[int] = None
    env = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, env, **kwargs):

        if self._initialized:
            return

        self.configuration = dict()
        self.env = env
        self.host = settings.redis.host
        self.port = settings.redis.port
        self.db = settings.redis.db
        self.expire_duration = settings.redis.expire_duration

        for key, val in kwargs.items():
            self.configuration[key.lower()] = val

        self._start()

        self._initialized = True

    def _start(self):
        if self.env == "testing":
            self._cache = _Cache()
            return
        if not self.host:
            return
        try:
            self._cache = aioredis.client.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                **self.configuration,
            )
        except aioredis.exceptions.ConnectionError as e:
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
        except aioredis.RedisError:
            return None

    async def set(self, key: str, val: str, expire_after=None) -> bool:
        if not self._cache:
            return False
        if not expire_after:
            expire_after = self.expire_duration
        result = await self._cache.set(key, val, ex=expire_after)
        return result
