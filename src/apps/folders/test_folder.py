import http
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.folders import errors
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture(scope="class")
async def applet_two_lucy_manager(
    global_session: AsyncSession, applet_two: AppletFull, tom: User, lucy: User
) -> AsyncGenerator[AppletFull, None]:
    await UserAppletAccessService(global_session, tom.id, applet_two.id).add_role(lucy.id, Role.MANAGER)
    await global_session.commit()
    yield applet_two
    await UserAppletAccessCRUD(global_session).remove_access_by_user_and_applet_to_role(
        lucy.id, [applet_two.id], [Role.MANAGER]
    )
    await global_session.commit()


@pytest.fixture
async def applet_not_in_folder(session: AsyncSession, tom: User, applet_minimal_data: AppletCreate):
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet not in folder"
    applet = await AppletService(session, tom.id).create(data)
    return applet


class TestFolder(BaseTest):
    fixtures = [
        "folders/fixtures/folders.json",
        "folders/fixtures/folders_applet.json",
    ]
    login_url = "/auth/login"
    workspace_url = "/workspaces/7484f34a-3acc-4ee6-8a94-fd7299502fa1"
    workspace_applets_url = f"{workspace_url}/applets"
    workspace_folder_applets_url = f"{workspace_url}/folders/{{folder_id}}/applets"
    list_url = f"{workspace_url}/folders"
    detail_url = f"{list_url}/{{id}}"
    pin_url = f"{detail_url}/pin/{{applet_id}}"
    applet_detail_url = "applets/{pk}"

    async def test_folder_list(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(self.list_url)

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]) == 3
        assert response.json()["count"] == 3
        assert response.json()["result"][0]["id"] == "ecf66358-a717-41a7-8027-807374307736"
        assert response.json()["result"][1]["id"] == "ecf66358-a717-41a7-8027-807374307732"
        assert response.json()["result"][2]["id"] == "ecf66358-a717-41a7-8027-807374307731"

    async def test_create_folder(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name="Daily applets")

        response = await client.post(self.list_url, data)

        assert response.status_code == http.HTTPStatus.CREATED
        assert response.json()["result"]["name"] == data["name"]
        assert response.json()["result"]["id"]

    async def test_create_folder_with_already_exists(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name="Morning applets")

        response = await client.post(self.list_url, data)

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == "Folder already exists."

    async def test_update_folder_name(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name="Daily applets")

        response = await client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["name"] == data["name"]

    async def test_update_folder_with_same_name_success(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name="Morning applets")

        response = await client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["name"] == data["name"]

    async def test_update_folder_name_with_already_exists(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name="Night applets")

        response = await client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == "Folder already exists."

    async def test_delete_folder(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

    async def test_delete_not_belonging_folder(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307733"))

        assert response.status_code == 403
        assert response.json()["result"][0]["message"] == "Access denied."

    async def test_delete_not_empty_folder(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307732"))
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == errors.FolderIsNotEmpty.message

    async def test_pin_applet(self, client: TestClient, applet_one: AppletFull, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.post(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307732",
                applet_id=applet_two_lucy_manager.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(
            self.workspace_folder_applets_url.format(folder_id="ecf66358-a717-41a7-8027-807374307732"),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 2
        assert response.json()["result"][0]["id"] == str(applet_two_lucy_manager.id)
        assert response.json()["result"][0]["isPinned"] is True
        assert response.json()["result"][1]["id"] == str(applet_one.id)
        assert response.json()["result"][1]["isPinned"] is True

    async def test_pin_applet_by_role_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.post(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307735",
                applet_id=applet_two_lucy_manager.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK

    async def test_unpin_applet_by_role_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        await client.post(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307735",
                applet_id=applet_two_lucy_manager.id,
            )
        )

        response = await client.delete(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307735",
                applet_id=applet_two_lucy_manager.id,
            )
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

    async def test_unpin_applet(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307732",
                applet_id=applet_one.id,
            )
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

    async def test_applet_delete(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.delete(
            self.applet_detail_url.format(pk=applet_one.id),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await client.get(
            self.workspace_folder_applets_url.format(folder_id="ecf66358-a717-41a7-8027-807374307732"),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1

    async def test_list_folders_by_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        resp = await client.get(self.list_url)

        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["count"] == 2
        assert resp.json()["result"][0]["name"] == "Empty"
        assert resp.json()["result"][1]["name"] == "Midnight applets"
        assert resp.json()["result"][1]["appletCount"] == 1

    async def test_create_folder_by_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        data = dict(name="manager")

        response = await client.post(self.list_url, data)

        assert response.status_code == http.HTTPStatus.CREATED
        assert response.json()["result"]["name"] == data["name"]

    async def test_update_folder_name_by_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        data = dict(name="hello")

        response = await client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307735"),
            data,
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["name"] == data["name"]

    async def test_delete_folder_by_manager(self, client: TestClient, applet_two_lucy_manager: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.delete(self.detail_url.format(id="ecf66358-a717-41a7-8027-999999999999"))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

    async def test_pin_applet_applet_not_in_folder(self, client: TestClient, applet_not_in_folder: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.post(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307732",
                applet_id=str(applet_not_in_folder.id),
            )
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == errors.AppletNotInFolder.message
