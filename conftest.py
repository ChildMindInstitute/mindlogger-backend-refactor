import os

import pytest
from alembic import command
from alembic.config import Config
from pytest_asyncio import is_async_test

alembic_configs = [Config("alembic.ini"), Config("alembic_arbitrary.ini")]


def before():
    os.environ["PYTEST_APP_TESTING"] = "1"
    for alembic_cfg in alembic_configs:
        command.upgrade(alembic_cfg, "head")


def after():
    for alembic_cfg in alembic_configs[::-1]:
        command.downgrade(alembic_cfg, "base")
    os.environ.pop("PYTEST_APP_TESTING")


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker)


def pytest_sessionstart():
    before()


def pytest_sessionfinish():
    after()
