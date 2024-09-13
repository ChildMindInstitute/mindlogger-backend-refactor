from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


class TestIntegrationRouter(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    async def test_create_integration_access_denied(
        self,
        client: TestClient,
        tom: User,
    ):
        create_loris_integration_url_data = {
            "applet_id": "8fb291b2-5ecf-4f21-ada8-04ca48451660",
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "https://loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 400

    async def test_create_integration(
        self,
        client: TestClient,
        tom: User,
    ):
        create_loris_integration_url_data = {
            "applet_id": "8fb291b2-5ecf-4f21-ada8-04ca48451660",
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "https://loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 400
