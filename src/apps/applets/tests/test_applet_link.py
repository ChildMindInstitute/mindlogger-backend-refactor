from apps.shared.test import BaseTest


class TestLink(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]
    login_url = "/auth/login"
    access_link_url = "applets/{applet_id}/access_link"

    async def test_applet_access_link_create_by_admin(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

        response = await client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            )
        )

        assert response.status_code == 200, response.json()

        assert isinstance(response.json()["result"]["link"], str)

        response = await client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            ),
            data=data,
        )
        assert response.status_code == 400

    async def test_applet_access_link_create_by_manager(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

    async def test_applet_access_link_create_by_coordinator(self, client):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")

        response = await client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

    async def test_applet_access_link_get(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200
        assert isinstance(response.json()["result"]["link"], str)

        response = await client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2"
            )
        )
        assert response.status_code == 404

    async def test_wrong_applet_access_link_get(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.access_link_url.format(
                applet_id="00000000-0000-0000-0000-000000000000"
            )
        )
        assert response.status_code == 404

    async def test_applet_access_link_delete(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.access_link_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 404

    async def test_applet_access_link_create_for_anonym(self, client):
        resp = await client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        # First delete link from fixtures
        resp = await client.delete(
            self.access_link_url.format(applet_id=applet_id)
        )
        data = {"require_login": False}
        resp = await client.post(
            self.access_link_url.format(applet_id=applet_id),
            data=data,
        )
        assert resp.status_code == 201
