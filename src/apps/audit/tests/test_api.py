import http

import pytest

from apps.applets.domain.applet_full import AppletFull
from apps.shared.test.client import TestClient
from apps.users.domain import User
from infrastructure.utility.opensearch_client import OpenSearchClientTest

URL = "/audit/applets/{applet_id}/events"


@pytest.fixture(autouse=True)
def reset_opensearch():
    OpenSearchClientTest._storage = {}
    OpenSearchClientTest._indices = set()
    OpenSearchClientTest.last_search_body = {}


async def test_unauthenticated_request_returns_401(client: TestClient, applet_one: AppletFull):
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


async def test_owner_can_export(client: TestClient, tom: User, applet_one: AppletFull):
    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK, response.json()
    body = response.json()
    assert body["result"] == []
    assert body["count"] == 0


async def test_manager_can_export(client: TestClient, lucy: User, applet_one_lucy_manager: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_manager.id))
    assert response.status_code == http.HTTPStatus.OK, response.json()


async def test_coordinator_is_forbidden(client: TestClient, lucy: User, applet_one_lucy_coordinator: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_coordinator.id))
    assert response.status_code == http.HTTPStatus.FORBIDDEN


async def test_editor_is_forbidden(client: TestClient, lucy: User, applet_one_lucy_editor: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_editor.id))
    assert response.status_code == http.HTTPStatus.FORBIDDEN


async def test_invalid_date_range_returns_422(client: TestClient, tom: User, applet_one: AppletFull):
    client.login(tom)
    response = await client.get(
        URL.format(applet_id=applet_one.id),
        dict(fromDate="2026-05-10", toDate="2026-05-01"),
    )
    assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY


async def test_returns_seeded_audit_event(client: TestClient, tom: User, applet_one: AppletFull):
    client.login(tom)

    OpenSearchClientTest._storage["audit-logs"] = [
        {
            "@timestamp": "2026-05-01T10:00:00+00:00",
            "event.id": "11111111-1111-1111-1111-111111111111",
            "event.action": "applet:answer:view",
            "user.id": str(tom.id),
            "curious.applet_id": [str(applet_one.id)],
        }
    ]

    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK
    body = response.json()
    assert body["count"] == 1
    assert body["result"][0]["event.action"] == "applet:answer:view"
    assert body["result"][0]["user.id"] == str(tom.id)
