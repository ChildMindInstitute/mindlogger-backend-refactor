import http
import uuid

from apps.folders.crud import FolderCRUD
from apps.folders.errors import FolderDoesNotExist
from apps.shared.test import BaseTest


class TestAppletMoveToFolder(BaseTest):
    fixtures = [
        "folders/fixtures/folders.json",
    ]
    login_url = "/auth/login"
    set_folder_url = "applets/set_folder"
    folders_applet_url = "applets/folders/{id}"

    async def test_move_to_folder(self, session, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(applet_one.id),
            folder_id="ecf66358-a717-41a7-8027-807374307731",
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.OK

        folders_ids = await FolderCRUD(session).get_applets_folder_id_in_workspace(
            tom.id,
            uuid.UUID(str(applet_one.id)),
        )
        assert len(folders_ids) == 1
        assert str(folders_ids[0]) == "ecf66358-a717-41a7-8027-807374307731"

    async def test_invalid_applet_move_to_folder(self, client, tom, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(uuid_zero),
            folder_id="ecf66358-a717-41a7-8027-807374307731",
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_move_to_not_accessible_folder(self, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(applet_one.id),
            folder_id="ecf66358-a717-41a7-8027-807374307733",
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert response.json()["result"][0]["message"] == "Access denied to folder."

    async def test_move_not_accessible_applet_to_folder(self, client, user, applet_one):
        await client.login(self.login_url, user.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(applet_one.id),
            folder_id="ecf66358-a717-41a7-8027-807374307732",
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        assert response.json()["result"][0]["message"] == "Access denied to edit applet in current workspace."

    async def test_remove_from_folder(self, session, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(applet_id=str(applet_one.id), folder_id=None)

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.OK

        folders_id = await FolderCRUD(session).get_applets_folder_id_in_workspace(tom.id, applet_one.id)
        assert len(folders_id) == 0

    async def test_move_to_folder__folder_does_not_exists(self, client, tom, applet_one, uuid_zero):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(applet_one.id),
            folder_id=str(uuid_zero),
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == FolderDoesNotExist.message

    async def test_move_to_folder_applet_already_moved(self, session, client, tom, applet_one):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = dict(
            applet_id=str(applet_one.id),
            folder_id="ecf66358-a717-41a7-8027-807374307731",
        )

        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.OK

        # move again
        response = await client.post(self.set_folder_url, data)
        assert response.status_code == http.HTTPStatus.OK

        folders_ids = await FolderCRUD(session).get_applets_folder_id_in_workspace(
            tom.id,
            uuid.UUID(str(applet_one.id)),
        )
        assert len(folders_ids) == 1
        assert str(folders_ids[0]) == "ecf66358-a717-41a7-8027-807374307731"
