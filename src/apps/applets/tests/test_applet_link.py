from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User
from config import settings


class TestLink(BaseTest):
    login_url = "/auth/login"
    access_link_url = "applets/{applet_id}/access_link"

    async def test_applet_access_link_create_by_admin(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(applet_id=applet_one.id),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

        response = await client.get(self.access_link_url.format(applet_id=applet_one.id))

        assert response.status_code == 200, response.json()

        assert isinstance(response.json()["result"]["link"], str)

        response = await client.post(
            self.access_link_url.format(applet_id=applet_one.id),
            data=data,
        )
        assert response.status_code == 400

    async def test_applet_access_link_create_by_manager(
        self, client: TestClient, applet_one_lucy_manager: AppletFull, lucy: User
    ):
        client.login(lucy)

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(applet_id=applet_one_lucy_manager.id),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

    async def test_applet_access_link_create_by_coordinator(
        self, client: TestClient, applet_one_lucy_coordinator: AppletFull, lucy: User
    ):
        client.login(lucy)

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(applet_id=applet_one_lucy_coordinator.id),
            data=data,
        )

        assert response.status_code == 201
        assert isinstance(response.json()["result"]["link"], str)

    async def test_applet_access_link_get(self, client: TestClient, applet_one_with_link: AppletFull, tom: User):
        client.login(tom)

        response = await client.get(self.access_link_url.format(applet_id=applet_one_with_link.id))
        assert response.status_code == 200
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.private_link
        assert response.json()["result"]["link"] == f"https://{domain}/{url_path}/{applet_one_with_link.link}"

    async def test_wrong_applet_access_link_get(self, client: TestClient, tom: User):
        client.login(tom)

        response = await client.get(self.access_link_url.format(applet_id="00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    async def test_applet_access_link_delete(self, client: TestClient, applet_one_with_link: AppletFull, tom: User):
        client.login(tom)

        response = await client.delete(self.access_link_url.format(applet_id=applet_one_with_link.id))
        assert response.status_code == 204

        response = await client.get(self.access_link_url.format(applet_id=applet_one_with_link.id))
        assert response.status_code == 404

    async def test_applet_access_link_delete_create(
        self, client: TestClient, applet_one_with_link: AppletFull, tom: User
    ):
        client.login(tom)

        response = await client.delete(self.access_link_url.format(applet_id=applet_one_with_link.id))
        assert response.status_code == 204

        data = {"require_login": True}
        response = await client.post(
            self.access_link_url.format(applet_id=applet_one_with_link.id),
            data=data,
        )

        assert response.status_code == 201

    async def test_applet_access_link_create_for_anonym(self, client: TestClient, applet_one: AppletFull, tom: User):
        resp = client.login(tom)
        applet_id = applet_one.id
        data = {"require_login": False}
        resp = await client.post(
            self.access_link_url.format(applet_id=applet_id),
            data=data,
        )
        assert resp.status_code == 201
