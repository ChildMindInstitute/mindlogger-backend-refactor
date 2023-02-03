from apps.applets.crud import AppletsCRUD
from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestAppletFolder(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
    ]
    login_url = "/auth/login"
    set_folder_url = "applets/set_folder"
    folders_applet_url = "applets/folders/{id}"

    @transaction.rollback
    async def test_folders_applet_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.folders_applet_url.format(id=2))

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 1
        assert response.json()["result"][0]["id"] == 1

        response = await self.client.get(self.folders_applet_url.format(id=1))

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 0

    @transaction.rollback
    async def test_move_to_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(applet_id=1, folder_id=1)

        response = await self.client.post(self.set_folder_url, data)
        assert response.status_code == 200

        applet = await AppletsCRUD().get_by_id(1)
        assert applet.folder_id == 1

    @transaction.rollback
    async def test_move_to_not_accessible_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(applet_id=1, folder_id=3)

        response = await self.client.post(self.set_folder_url, data)
        assert response.status_code == 422
        assert (
            response.json()["result"][0]["message"]["en"]
            == "Access denied to folder."
        )

    @transaction.rollback
    async def test_move_not_accessible_applet_to_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(applet_id=4, folder_id=2)

        response = await self.client.post(self.set_folder_url, data)
        assert response.status_code == 422
        assert (
            response.json()["result"][0]["message"]["en"]
            == "Access denied to applet."
        )

    @transaction.rollback
    async def test_remove_from_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(applet_id=1, folder_id=None)

        response = await self.client.post(self.set_folder_url, data)
        assert response.status_code == 200

        applet = await AppletsCRUD().get_by_id(1)
        assert applet.folder_id is None
