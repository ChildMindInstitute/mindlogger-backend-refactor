import pytest
from testcontainers.redis import RedisContainer


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
