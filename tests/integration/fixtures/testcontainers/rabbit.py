from urllib.parse import unquote

import pytest
from testcontainers.rabbitmq import RabbitMqContainer


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
