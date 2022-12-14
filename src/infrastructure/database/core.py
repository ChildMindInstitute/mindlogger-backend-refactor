import asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from config import settings

__all__ = ["engine", "session_manager"]

engine = create_async_engine(
    settings.database.url,
    future=True,
    pool_pre_ping=True,
    echo=False,
    pool_size=settings.database.pool_size,
)


class SessionManager:
    def __init__(self):
        self.session = None

    def get_session(self):
        if not self.session:
            async_session_factory = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            AsyncScopedSession = async_scoped_session(
                async_session_factory, scopefunc=asyncio.current_task
            )
            self.session = AsyncScopedSession()
        return self.session


session_manager = SessionManager()
