from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestAppletLink(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]
    login_url = "/auth/login"
    access_link_url = "applets/{applet_id}/access_link"

    @transaction.rollback
    async def test_applet_access_link_create(self):
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
        assert response.status_code == 422

    @transaction.rollback
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
        assert response.status_code == 200
        assert response.json()["result"]["link"] is None

    @transaction.rollback
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
        assert response.status_code == 200
        assert response.json()["result"]["link"] is None
