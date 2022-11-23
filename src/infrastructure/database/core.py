from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from config import settings

__all__ = ["get_session", "engine"]


engine = create_async_engine(
    settings.database.url, future=True, pool_pre_ping=True, echo=False
)


def get_session() -> AsyncSession:
    async_session_factory = sessionmaker(engine, class_=AsyncSession)
    AsyncScopedSession = async_scoped_session(
        async_session_factory, scopefunc=lambda: None
    )
    return AsyncScopedSession()
