import asyncio
import json

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from config import settings

__all__ = ["engine", "session_manager", "transaction"]

engine = create_async_engine(
    settings.database.url,
    future=True,
    pool_pre_ping=True,
    echo=False,
    pool_size=settings.database.pool_size,
    json_serializer=lambda x: json.dumps(x, ensure_ascii=False),
    json_deserializer=lambda x: json.loads(x),
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
            self.session.transaction_count = 0
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None


session_manager = SessionManager()


class TransactionManager:
    def commit(self, func):
        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            result = None
            try:
                async with session.begin_nested():
                    session.transaction_count += 1
                    try:
                        result = await func(*args, **kwargs)
                    except Exception:
                        raise
                    finally:
                        session.transaction_count -= 1
            except Exception:
                raise
            finally:
                if session.transaction_count == 0:
                    await session.commit()
                    await session_manager.close()
                return result

        return _wrap

    def atomic(self, func):
        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            async with session.begin_nested():
                session.transaction_count += 1
                try:
                    await func(*args, **kwargs)
                except Exception:
                    raise
                finally:
                    session.transaction_count -= 1
                    await session.rollback()

        return _wrap

    def rollback(self, func):
        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            try:
                async with session.begin_nested():
                    session.transaction_count += 1
                    try:
                        await func(*args, **kwargs)
                    except Exception:
                        raise
                    finally:
                        session.transaction_count -= 1
                        await session.rollback()
            except Exception:
                raise
            finally:
                if session.transaction_count == 0:
                    await session_manager.close()

        return _wrap


transaction = TransactionManager()
