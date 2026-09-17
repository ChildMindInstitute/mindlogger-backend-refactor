# tests/integration/conftest.py
import json
from functools import lru_cache
from urllib.parse import urlparse, unquote
import pytest
import taskiq_fastapi
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from testcontainers.redis import RedisContainer

from apps.shared.test.client import TestClient
from broker import broker
from infrastructure.app import create_app
from infrastructure.database import Base, session_manager
from infrastructure.database.deps import get_session


@pytest.fixture(scope="session")
def app(db_session) -> FastAPI:
    """Create the FastAPI app with the test database session."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    return app

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # app.dependency_overrides[get_session] = lambda: session
    taskiq_fastapi.populate_dependency_context(broker, app)
    client = TestClient(app)
    return client

############################################################
## testcontainers
############################################################

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


@pytest.fixture(scope="session")
async def db_session(db_url, apply_migrations):
    """Get a session to the database.  Used to replace get_session"""
    session_maker = session_manager.get_session(db_url)
    async with session_maker() as session:
        yield session

@pytest.fixture(scope="session")
async def session(db_session):
    """Alias to make old tests work"""
    yield db_session

@pytest.fixture(autouse=True)
async def clean_tables(db_session):
    """Automatically clean up the database before every single test to ensure isolation."""
    yield
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()


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