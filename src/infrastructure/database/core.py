import json

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import settings

__all__ = ["session_manager", "atomic", "build_engine"]


def build_engine(uri: str) -> AsyncEngine:
    return create_async_engine(
        uri,
        future=True,
        pool_pre_ping=True,
        echo=False,
        poolclass=AsyncAdaptedQueuePool,
        json_serializer=lambda x: json.dumps(x),
        json_deserializer=lambda x: json.loads(x),
    )


class SessionManager:
    def get_session(self, uri: str = settings.database.url) -> sessionmaker:
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
