import datetime
import typing

import aioredis


class _Cache(aioredis.Redis):
    _storage = dict()

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
    configuration = dict()
    _cache: typing.Optional[aioredis.Redis] = None
    host: typing.Optional[str] = None
    port: typing.Optional[int] = None
    db: typing.Optional[int] = None
    expire_duration: typing.Optional[int] = None
    env = None

    def create(self, env, **kwargs):
        self.env = env
        self.configuration = dict()
        for key, val in kwargs.items():
            if key.lower() == "host":
                self.host = val
            elif key.lower() == "port":
                self.port = val
            elif key.lower() == "db":
                self.db = val
            elif key.lower() == "expire_duration":
                self.expire_duration = val
            else:
                self.configuration[key.lower()] = val
        self._start()

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
                from sentry_sdk import capture_exception

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
