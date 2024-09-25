import json

from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


class TestIntegrationRouter(BaseTest):
    async def test_create_integration_access_denied(
        self,
        client: TestClient,
        tom: User,
    ):
        create_loris_integration_url_data = {
            "applet_id": "8fb291b2-5ecf-4f21-ada8-04ca48451660",
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 403

    async def test_create_integration_success(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
    ):
        create_loris_integration_url_data = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 201

    async def test_create_integration_wrong_parameters_for_type(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
    ):
        create_loris_integration_url_data = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
            "configuration": {
                "api_endpoint": "loris.cmiml.net",
                "api_key": "lorisfrontadmin",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        dict_response = json.loads(response.text)
        assert len(dict_response["result"]) == 11
        assert response.status_code == 422

    async def test_retrieve_integration(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
    ):
        create_loris_integration_url_data = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 201

        retrieve_loris_integration_url_query = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
        }
        response = await client.get("integrations/", query=retrieve_loris_integration_url_query)
        dict_response = json.loads(response.text)
        assert response.status_code == 200
        assert dict_response["integrationType"] == "LORIS"
        assert dict_response["appletId"] == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        assert dict_response["configuration"]["hostname"] == "loris.cmiml.net"
        assert dict_response["configuration"]["username"] == "lorisfrontadmin"
        assert dict_response["configuration"]["project"] == "loris_project"
        assert "password" not in dict_response.keys()


    async def test_delete_integration(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
    ):
        create_loris_integration_url_data = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
            "configuration": {
                "hostname": "loris.cmiml.net",
                "username": "lorisfrontadmin",
                "password": "password",
                "project": "loris_project",
            },
        }
        client.login(tom)
        response = await client.post("integrations/", data=create_loris_integration_url_data)
        assert response.status_code == 201

        retrieve_loris_integration_url_query = {
            "applet_id": applet_one.id,
            "integration_type": "LORIS",
        }
        response = await client.get("integrations/", query=retrieve_loris_integration_url_query)
        dict_response = json.loads(response.text)
        assert response.status_code == 200
        assert dict_response["integrationType"] == "LORIS"
        assert dict_response["appletId"] == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        assert dict_response["configuration"]["hostname"] == "loris.cmiml.net"
        assert dict_response["configuration"]["username"] == "lorisfrontadmin"
        assert dict_response["configuration"]["project"] == "loris_project"
        assert "password" not in dict_response.keys()

        delete_loris_integration_url_query = {
            "integration_type": "LORIS",
        }
        await client.delete(f"integrations/applet/{applet_one.id}", query=delete_loris_integration_url_query)
        assert response.status_code == 200

        response = await client.get("integrations/", query=retrieve_loris_integration_url_query)
        assert response.status_code == 400
        result = json.loads(response.text)
        assert result["result"][0]["message"] == 'The specified integration type `LORIS` does not exist for applet `92917a56-d586-4613-b7aa-991f2c4b15b1`'
