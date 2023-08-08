import asyncio
import json
from functools import wraps

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import settings

__all__ = [
    "engine",
    "session_manager",
    "rollback",
    "atomic",
    "rollback_with_session",
]


def build_engine(uri: str):
    return create_async_engine(
        uri,
        future=True,
        pool_pre_ping=True,
        echo=False,
        poolclass=NullPool,
        json_serializer=lambda x: json.dumps(x),
        json_deserializer=lambda x: json.loads(x),
    )


engine = create_async_engine(settings.database.url)


class SessionManager:
    def __init__(self):
        self.test_session = None

    def get_session(self, uri: str = settings.database.url):
        if settings.env == "testing":
            return self._get_test_session(uri)
        return self._get_session(uri)

    def get_session_factory(self, uri: str):
        return sessionmaker(
            build_engine(uri),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    def _get_test_session(self, uri: str):
        if self.test_session:
            return self.test_session
        async_session_factory = sessionmaker(
            build_engine(uri), class_=AsyncSession, expire_on_commit=False
        )
        AsyncScopedSession = async_scoped_session(
            async_session_factory, scopefunc=asyncio.current_task
        )
        self.test_session = AsyncScopedSession()
        return self.test_session

    def _get_session(self, uri: str):
        return async_scoped_session(
            self.get_session_factory(uri), asyncio.current_task
        )


session_manager = SessionManager()


class atomic:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if settings.env != "testing":
            if not exc_type:
                await self.session.commit()
            else:
                await self.session.rollback()
                raise
        else:
            if exc_type:
                await self.session.rollback()
                raise


def rollback(func):
    @wraps(func)
    async def _wrap(*args, **kwargs):
        session = session_manager.get_session()
        try:
            await func(*args, **kwargs)
        except Exception:
            raise
        finally:
            await session.rollback()

    return _wrap


def rollback_with_session(func):
    @wraps(func)
    async def _wrap(*args, **kwargs):
        session = session_manager.get_session()
        kwargs["session"] = session
        try:
            await func(*args, **kwargs)
        except Exception:
            raise
        finally:
            await session.rollback()

    return _wrap


async def get_specific_session(url: str):
    session_maker = session_manager.get_session(url)
    if settings.env == "testing":
        yield session_maker
    else:
        async with session_maker() as session:
            yield session
