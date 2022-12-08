import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config

alembic_cfg = Config("alembic.ini")
os.environ.setdefault("env", "testing")


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
