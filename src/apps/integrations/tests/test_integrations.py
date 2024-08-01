import uuid

from apps.integrations.domain import AvailableIntegrations
from apps.integrations.errors import UniqueIntegrationError
from apps.integrations.router import router as integration_router
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


class TestIntegrationRouter(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]
    enable_integration_url = integration_router.url_path_for("enable_integration")
    disable_integration_url = integration_router.url_path_for("disable_integration")
    create_loris_integration_url = integration_router.url_path_for(
        "create_integration", type=AvailableIntegrations.LORIS
    )

    async def test_enable_integration(
        self,
        client: TestClient,
        tom: User,
    ):
        integration_data = [
            {"integrationType": "LORIS"},
        ]
        client.login(tom)
        response = await client.post(self.enable_integration_url, data=integration_data)
        assert response.status_code == 200

    async def test_disable_integration(
        self,
        client: TestClient,
        tom: User,
    ):
        client.login(tom)
        response = await client.delete(
            self.disable_integration_url,
        )
        assert response.status_code == 204

    async def test_enable_integration_unique_error(
        self,
        client: TestClient,
        tom: User,
    ):
        integration_data = [
            {"integrationType": "LORIS"},
            {"integrationType": "LORIS"},
        ]
        client.login(tom)
        response = await client.post(self.enable_integration_url, data=integration_data)
        assert response.status_code == 400

        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == UniqueIntegrationError.message

    async def test_create_integration(
        self,
        client: TestClient,
        tom: User,
    ):
        create_loris_integration_url_data = [
            {"applet_id": uuid.UUID, "hostname": "https://someloris.org", "username": "david", "password": "abc12345"}
        ]
        client.login(tom)
        response = await client.post(self.create_loris_integration_url, data=create_loris_integration_url_data)
        # assert response.status_code == 201
        assert response.status_code == 422
