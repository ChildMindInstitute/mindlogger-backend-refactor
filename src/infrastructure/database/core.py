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
    json_serializer=lambda x: json.dumps(x),
    json_deserializer=lambda x: json.loads(x),
)


class SessionManager:
    def __init__(self):
        self.session = None

    def get_session(self):
        """
        session = SessionManager().get_session()

        Returns async scoped session with counter for transactions.
        """
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
        """
        await SessionManager().close()

        It will cose session and remove cached session.
        """
        if self.session:
            await self.session.close()
            self.session = None


session_manager = SessionManager()


class TransactionManager:
    def commit(self, func):
        """
        @commit
        async def initial_method(*args, **kwargs):
            pass

        This decorator forcibly commits the database session.
        Use it in initial database interaction(ex. in middlewares) to open
         session.
        Transaction counter is used to understand when to commit changes and
         close session.
        """

        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            session.transaction_count += 1
            try:
                result = await func(*args, **kwargs)
                session.transaction_count -= 1
                if session.transaction_count == 0:
                    await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                raise e

        return _wrap

    def atomic(self, func):
        """
        @atomic
        async def create_doc(*args, **kwargs):
            pass

        Creates savepoint to rollback or keep it until the latest commit.
        Use it to wrap atomic database interactions to avoid false commits.
        """

        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            async with session.begin_nested():
                try:
                    await func(*args, **kwargs)
                finally:
                    await session.rollback()

        return _wrap

    def rollback(self, func):
        """
        @rollback
        async def test_action(*args, **kwargs):
            pass

        This decorator forcibly rollbacks the database session.
        Use it in tests to rollback.
        Transaction counter is used to close session.
        """

        async def _wrap(*args, **kwargs):
            session = session_manager.get_session()
            session.transaction_count += 1
            try:
                await func(*args, **kwargs)
            finally:
                await session.rollback()
            session.transaction_count -= 1

        return _wrap


transaction = TransactionManager()
