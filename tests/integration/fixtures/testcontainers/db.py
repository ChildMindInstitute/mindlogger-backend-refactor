import os
from typing import AsyncGenerator
from urllib.parse import unquote, urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from testcontainers.postgres import PostgresContainer

from infrastructure.database import build_engine


@pytest.fixture(scope="session", autouse=True)
def postgres_container():
    """Create a Postgres container for the test session."""
    with PostgresContainer("postgres:16") as pg:
        parsed = urlparse(pg.get_connection_url())

        # Set env vars for container
        if not parsed.scheme:
            raise ValueError("Connection string is missing a scheme")
        if not parsed.hostname:
            raise ValueError("Connection string is missing a host")
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("DATABASE__USERNAME", parsed.username)
            monkeypatch.setenv("DATABASE__PASSWORD", unquote(parsed.password))
            monkeypatch.setenv("DATABASE__HOST", parsed.hostname)
            monkeypatch.setenv("DATABASE__PORT", str(parsed.port or 5432))
            monkeypatch.setenv("DATABASE__DB", parsed.path.lstrip("/"))
        yield pg


@pytest.fixture(scope="session", autouse=True)
def arb_postgres_container():
    """Create a Postgres container for the test session."""
    with PostgresContainer("postgres:16") as pg:
        os.environ["PYTEST_ARB_URL"] = change_pycopg2_to_asyncpg(pg.get_connection_url())
        os.environ["PYTEST_APP_TESTING"] = "true"
        yield pg


@pytest.fixture(scope="session", autouse=True)
async def ensure_pgcrypto(db_engine):
    """Ensure pgcrypto extension is installed."""
    async with db_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))


def change_pycopg2_to_asyncpg(url: str) -> str:
    return url.replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
def db_url(postgres_container):
    """Get the DB URL connection string and change to asyncpg"""
    return change_pycopg2_to_asyncpg(postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def arb_db_url(arb_postgres_container):
    """Get the DB URL connection string and change to asyncpg"""
    return change_pycopg2_to_asyncpg(arb_postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def apply_migrations(postgres_container, db_url, arb_db_url):
    """Run alembic upgrade head against the test container once per session."""

    configs = [Config("alembic.ini"), Config("alembic_arbitrary.ini")]
    for cfg in configs:
        cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(cfg, "head")

    yield
    # no need to downgrade — container is thrown away after session


@pytest.fixture(scope="session")
async def db_engine(db_url) -> AsyncEngine:
    return build_engine(db_url)


@pytest.fixture(scope="session")
async def arb_db_engine(arb_db_url) -> AsyncEngine:
    return build_engine(arb_db_url)


# ==============================================
# Integration test isolation methods
# connection() and savepoint() work together with session() to
# create a wrapper transaction that will rollback every operation for each test
# ==============================================
# @pytest.fixture
# async def connection(db_engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
#     """Outer transaction — this is what gets rolled back at the very end."""
#     async with db_engine.connect() as conn:
#         async with conn.begin():
#             yield conn
#             # transaction auto-rolls-back on exit if not committed —
#             # but we never commit it, so it's implicitly discarded here.
#
#
# @pytest.fixture
# async def savepoint(connection: AsyncConnection) -> AsyncGenerator[AsyncConnection, None]:
#     """Nested SAVEPOINT that auto-restarts itself if the session commits."""
#     await connection.begin_nested()
#
#     @event.listens_for(connection.sync_connection, "after_transaction_end")
#     def restart_savepoint(sync_conn, transaction):
#         if connection.closed:
#             return
#         if not connection.in_nested_transaction():
#             connection.sync_connection.begin_nested()
#
#     yield connection
#
#
# @pytest.fixture
# async def session(savepoint: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
#     """The session tests actually use."""
#     async with AsyncSession(bind=savepoint) as s:
#         yield s

@pytest.fixture
async def connection(db_engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Outer transaction — this is what gets rolled back at the very end."""
    async with db_engine.connect() as conn:
        async with conn.begin():
            yield conn


@pytest.fixture
async def savepoint(connection: AsyncConnection) -> AsyncGenerator[AsyncConnection, None]:
    """Nested SAVEPOINT — just establishes the initial savepoint."""
    await connection.begin_nested()
    yield connection


@pytest.fixture
async def db_session(savepoint: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """The session tests actually use. Owns the restart-savepoint listener."""
    async_session = AsyncSession(bind=savepoint)

    @event.listens_for(async_session.sync_session, "after_transaction_end")
    def restart_savepoint(sync_session, transaction):
        sync_conn = savepoint.sync_connection
        if sync_conn.closed:
            return
        if not sync_conn.in_nested_transaction():
            sync_conn.begin_nested()

    async with async_session as s:
        yield s