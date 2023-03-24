import asyncio
import json

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import settings

__all__ = ["engine", "session_manager", "rollback", "atomic"]

engine = create_async_engine(
    settings.database.url,
    future=True,
    pool_pre_ping=True,
    echo=False,
    poolclass=NullPool,
    json_serializer=lambda x: json.dumps(x),
    json_deserializer=lambda x: json.loads(x),
)

async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class SessionManager:
    def __init__(self):
        self.test_session = None

    def get_session(self):
        if settings.env == "testing":
            return self._get_test_session()
        return self._get_session()

    def _get_test_session(self):
        if self.test_session:
            return self.test_session
        async_session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        AsyncScopedSession = async_scoped_session(
            async_session_factory, scopefunc=asyncio.current_task
        )
        self.test_session = AsyncScopedSession()
        return self.test_session

    def _get_session(self):
        return async_scoped_session(
            async_session_factory, asyncio.current_task
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
                await self.session.close()
            else:
                await self.session.rollback()
                await self.session.close()
                raise exc_type(exc_val)
        else:
            if exc_type:
                await self.session.rollback()
                raise exc_type


def rollback(func):
    async def _wrap(*args, **kwargs):
        session = session_manager.get_session()
        await func(*args, **kwargs)
        await session.rollback()

    return _wrap
