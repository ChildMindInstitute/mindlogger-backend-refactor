import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config

alembic_configs = [Config("alembic.ini"), Config("alembic_arbitrary.ini")]


def before():
    os.environ["PYTEST_APP_TESTING"] = "1"
    for alembic_cfg in alembic_configs:
        command.upgrade(alembic_cfg, "head")


def after():
    for alembic_cfg in alembic_configs:
        command.downgrade(alembic_cfg, "base")
    os.environ.pop("PYTEST_APP_TESTING")


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


def pytest_sessionstart():
    before()


def pytest_sessionfinish():
    after()
