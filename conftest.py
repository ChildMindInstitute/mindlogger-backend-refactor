import asyncio

import pytest
from alembic import command
from alembic.config import Config

alembic_cfg = Config("alembic.ini")


def before():
    command.upgrade(alembic_cfg, "head")


def after():
    command.downgrade(alembic_cfg, "base")


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
