import json
from functools import cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings

__all__ = ["session_manager", "atomic", "build_engine"]


@cache
def build_engine(uri: str) -> AsyncEngine:
    return create_async_engine(
        uri,
        future=True,
        pool_pre_ping=True,
        echo=False,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.pool_overflow_size,
        pool_timeout=settings.database.pool_timeout,
        json_serializer=lambda x: json.dumps(x),
        json_deserializer=lambda x: json.loads(x),
    )


class SessionManager:
    @staticmethod
    def get_session(uri: str = settings.database.url) -> sessionmaker:
        return sessionmaker(
            build_engine(uri),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )


session_manager = SessionManager()


class atomic:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            return
        if not exc_type:
            await self.session.commit()
        else:
            await self.session.rollback()
            raise
