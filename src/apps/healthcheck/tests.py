import pytest

from apps.healthcheck.domain import EmergencyMessageType
from apps.shared.test import BaseTest
from apps.users import User


@pytest.fixture
def emergency_message_payload() -> dict:
    return {
        "os": {
            "name": "ios",
            "version": "14.0.0",
        },
        "appVersion": "1.0.0",
    }


class TestHealthcheck(BaseTest):
    async def test_readiness(self, client):
        response = await client.get("readiness")
        assert response.status_code == 200
        assert response.content == b"Readiness - OK!"

    async def test_liveness(self, client):
        response = await client.get("liveness")
        assert response.status_code == 200
        assert response.content == b"Liveness - OK!"

    async def test_emergency_message__unauthorized(self, client, emergency_message_payload):
        response = await client.post("emergency-message", data=emergency_message_payload)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"message", "type", "dismissible"}
        assert data["message"] is None
        assert data["type"] is None
        assert data["dismissible"] is True

    async def test_emergency_message__authorized(self, client, emergency_message_payload, tom: User):
        client.login(tom)
        response = await client.post("emergency-message", data=emergency_message_payload)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"message", "type", "dismissible"}
        assert data["message"] is None
        assert data["type"] is None
        assert data["dismissible"] is True

    async def test_emergency_message__authorized_testflag(self, client, emergency_message_payload, tom: User):
        client.login(tom)
        response = await client.post("emergency-message", data=emergency_message_payload, query={"test": 1})
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"message", "type", "dismissible"}
        assert data["message"] is not None
        assert data["type"] == EmergencyMessageType.blocker
        assert data["dismissible"] is False
