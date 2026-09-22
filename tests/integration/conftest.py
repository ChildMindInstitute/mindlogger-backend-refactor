import json
import uuid
from pathlib import Path
from typing import Callable

import pytest
import taskiq_fastapi
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.domain.token import JWTClaim
from apps.authentication.services import AuthenticationService
from apps.users import User
from broker import broker
from infrastructure.app import create_app
from infrastructure.database.deps import get_session

pytest_plugins = [
    "tests.integration.fixtures.testcontainers.db",
    "tests.integration.fixtures.testcontainers.rabbit",
    "tests.integration.fixtures.testcontainers.redis",
]


@pytest.fixture(scope="session")
def app(apply_migrations) -> FastAPI:
    """Create the FastAPI app with the test database session."""
    app = create_app()
    return app


@pytest.fixture(autouse=True)
def setup_app_session(app: FastAPI, db_session: AsyncSession):
    """Override the get_session dependency with the test session."""
    app.dependency_overrides[get_session] = lambda: db_session
    # TODO Figure out what this does and document it
    taskiq_fastapi.populate_dependency_context(broker, app)


@pytest.fixture
def create_authorized_client(app: FastAPI) -> Callable[[User | uuid.UUID], TestClient]:
    """Factory fixture to create an authenticated FastAPI TestClient"""

    def _create_client(user: User | uuid.UUID) -> TestClient:
        if isinstance(user, User):
            sub = user.id
        else:
            sub = user

        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(sub),
                JWTClaim.rjti: str(uuid.uuid4()),
            }
        )

        client = TestClient(app, headers={"Authorization": f"Bearer {access_token}"})
        return client

    return _create_client


FIXTURES_ROOT = Path("tests/integration")
# Tables to skip when loading db fixture data
SKIP_TABLES = {"users"}

# Fixture helpers
async def _load_fixture_file(db_session, relative_path: str):
    path = FIXTURES_ROOT / relative_path
    data = json.loads(path.resolve()).read_text()
    for datum in data:
        if datum["table"] in SKIP_TABLES:
            continue
        columns = ", ".join(f'"{f}"' for f in datum["fields"])
        placeholders = ", ".join(f":{f}" for f in datum["fields"])

        query = text(f'INSERT INTO "{datum["table"]}" ({columns}) VALUES ({placeholders})')
        await db_session.execute(query, datum["fields"])

    await db_session.commit()


@pytest.fixture(autouse=True)
async def load_fixtures(request, db_session):
    """
    Fixture to load json data into the database.  This is a holdover/improved version of the
    method used in the legacy tests without the BaseTest class.

    To use, annotate a test function with:

    @pytest.mark.db_fixtures(["orders.json", "customers.json"])
    async def test_order_flow(db_session): ...

    All data is cleared after each test.
    """
    marker = request.node.get_closest_marker("fixtures")
    fixture_files = marker.args[0] if marker else []
    for f in fixture_files:
        await _load_fixture_file(db_session, f)
    yield
