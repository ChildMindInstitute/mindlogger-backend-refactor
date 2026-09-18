# tests/integration/conftest.py
from typing import AsyncGenerator
from urllib.parse import unquote, urlparse
from warnings import deprecated

import pytest
import taskiq_fastapi
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from testcontainers.redis import RedisContainer

from apps.shared.test.client import TestClient
from broker import broker
from infrastructure.app import create_app
from infrastructure.database import build_engine, session_manager
from infrastructure.database.deps import get_session


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create the FastAPI app with the test database session."""
    app = create_app()
    return app


@pytest.fixture
def client(app: FastAPI, session: AsyncSession) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    taskiq_fastapi.populate_dependency_context(broker, app)
    client = TestClient(app)
    return client


# =========================================================
## testcontainers
# =========================================================


## Postgres
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


@pytest.fixture(scope="session")
def db_url(postgres_container):
    """Get the DB URL connection string and change to asyncpg"""
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
def apply_migrations(postgres_container, db_url):
    """Run alembic upgrade head against the test container once per session."""
    # TODO Arbitrary server
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")
    yield
    # no need to downgrade — container is thrown away after session


@deprecated("use session")
@pytest.fixture(scope="session")
async def db_session(db_url, apply_migrations):
    """Get a session to the database.  Used to replace get_session"""
    session_maker = session_manager.get_session(db_url)
    async with session_maker() as session:
        yield session


@pytest.fixture
async def engine(db_url) -> AsyncEngine:
    return build_engine(db_url)


# ==============================================
# Integration test isolation methods
# connection() and savepoint() work together with session() to
# create a wrapper transaction that will rollback every operation for each test
# ==============================================
@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Outer transaction — this is what gets rolled back at the very end."""
    async with engine.connect() as conn:
        async with conn.begin():
            yield conn
            # transaction auto-rolls-back on exit if not committed —
            # but we never commit it, so it's implicitly discarded here.


@pytest.fixture
async def savepoint(connection: AsyncConnection) -> AsyncGenerator[AsyncConnection, None]:
    """Nested SAVEPOINT that auto-restarts itself if the session commits."""
    await connection.begin_nested()

    @event.listens_for(connection.sync_connection, "after_transaction_end")
    def restart_savepoint(sync_conn, transaction):
        if connection.closed:
            return
        if not connection.in_nested_transaction():
            connection.sync_connection.begin_nested()

    yield connection


@pytest.fixture
async def session(savepoint: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """The session tests actually use."""
    async with AsyncSession(bind=savepoint) as s:
        yield s


# @pytest.fixture
# async def session(engine: AsyncEngine) -> AsyncGenerator:
#     """
#     Fixture to provide a database session scoped for testing purposes.
#
#     This fixture is designed to enable safe and isolated database transactions during tests by
#     leveraging SQLAlchemy's nested transactions. It ensures that each test runs in its own
#     database context and any changes made during the test are rolled back after the test completes.
#     This prevents side effects between tests and maintains database consistency.
#
#     Attributes:
#         engine (AsyncEngine): The asynchronous SQLAlchemy engine used to manage database connections.
#
#     Yields:
#         AsyncSession: An asynchronous SQLAlchemy session bound to a nested transaction, used for
#         performing database operations in test cases.
#     """
#     async with engine.begin() as conn:
#         conn = cast(AsyncConnection, conn)
#         await conn.begin_nested()
#
#         async_session = AsyncSession(bind=conn)
#
#         @event.listens_for(async_session.sync_session, "after_transaction_end")
#         def end_savepoint(session: Session, transaction: SessionTransaction) -> None:
#             nonlocal conn
#             if conn.closed:
#                 return
#             if not conn.in_nested_transaction():
#                 if conn.sync_connection:
#                     conn.sync_connection.begin_nested()
#
#         async with async_session:
#             yield async_session
#
#         await conn.rollback()

# @pytest.fixture(scope="session")
# async def session(db_session):
#     """Alias to make old tests work"""
#     yield db_session

# @pytest.fixture(autouse=True)
# async def clean_tables(db_session):
#     """Automatically clean up the database before every single test to ensure isolation."""
#     yield
#     for table in reversed(Base.metadata.sorted_tables):
#         await db_session.execute(table.delete())
#     await db_session.commit()


## RabbitMQ
@pytest.fixture(scope="session", autouse=True)
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:3-management") as rmq:
        params = rmq.get_connection_params()
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("RABBITMQ__USER", rmq.username)
            monkeypatch.setenv("RABBITMQ__PASSWORD", unquote(rmq.password))
            monkeypatch.setenv("RABBITMQ__HOST", params.host)
            monkeypatch.setenv("RABBITMQ__PORT", str(params.port))
            monkeypatch.setenv("RABBITMQ__USE_SSL", "false")

        yield rmq


@pytest.fixture(scope="session")
def rabbitmq_connection_params(rabbitmq_container):
    return rabbitmq_container.get_connection_params()


## Redis
@pytest.fixture(scope="session", autouse=True)
def redis_container():
    with RedisContainer("redis:7.2", port=6379) as redis_container:
        # Setup redis environment variables
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("REDIS__HOST", redis_container.get_container_host_ip())

        yield redis_container


@pytest.fixture(scope="session")
def redis_client(redis_container):
    client = redis_container.get_client()

    yield client


@pytest.fixture(scope="session")
def redis_url(redis_container):
    host = redis_container.get_container_host_ip()
    return f"redis://{host}:{6379}/db0"


@pytest.fixture(autouse=True)
def flush_redis(redis_client):
    """Automatically flushes the database before every single test to ensure isolation."""
    redis_client.flushdb()
