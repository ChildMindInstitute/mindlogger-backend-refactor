from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestAppletLink(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]
    login_url = "/auth/login"
    access_link_url = "applets/{applet_id}/access_link"

    @rollback
    async def test_applet_access_link_create_by_admin(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = {"require_login": True}
        response = await self.client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert type(response.json()["result"]["link"]) == str

        response = await self.client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            )
        )

        assert response.status_code == 200, response.json()

        assert type(response.json()["result"]["link"]) == str

        response = await self.client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            data=data,
        )
        assert response.status_code == 400

    @rollback
    async def test_applet_access_link_create_by_manager(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        data = {"require_login": True}
        response = await self.client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert type(response.json()["result"]["link"]) == str

    @rollback
    async def test_applet_access_link_create_by_coordinator(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")

        response = await self.client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        data = {"require_login": True}
        response = await self.client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert type(response.json()["result"]["link"]) == str

    @rollback
    async def test_applet_access_link_get(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200
        assert type(response.json()["result"]["link"]) == str

        response = await self.client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            )
        )
        assert response.status_code == 404

    @rollback
    async def test_wrong_applet_access_link_get(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.access_link_url.format(
                applet_id="00000000-0000-0000-0000-000000000000"
            )
        )
        assert response.status_code == 404

    @rollback
    async def test_applet_access_link_delete(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        response = await self.client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 404
