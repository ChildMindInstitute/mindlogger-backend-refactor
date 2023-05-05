from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestFolder(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "folders/fixtures/folders_applet.json",
    ]
    login_url = "/auth/login"
    list_url = "/folders"
    detail_url = "/folders/{id}"
    pin_url = f"{detail_url}/pin/{{applet_id}}"

    @rollback
    async def test_folder_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.list_url)

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2
        assert response.json()["count"] == 2
        assert (
            response.json()["result"][0]["id"]
            == "ecf66358-a717-41a7-8027-807374307732"
        )
        assert (
            response.json()["result"][1]["id"]
            == "ecf66358-a717-41a7-8027-807374307731"
        )

    @rollback
    async def test_create_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(name="Daily applets")

        response = await self.client.post(self.list_url, data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["name"] == data["name"]
        assert response.json()["result"]["id"]

    @rollback
    async def test_create_folder_with_already_exists(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(name="Morning applets")

        response = await self.client.post(self.list_url, data)

        assert response.status_code == 400, response.json()
        assert (
            response.json()["result"][0]["message"] == "Folder already exists."
        )

    @rollback
    async def test_update_folder_name(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(name="Daily applets")

        response = await self.client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == data["name"]

    @rollback
    async def test_update_folder_with_same_name_success(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(name="Morning applets")

        response = await self.client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == data["name"]

    @rollback
    async def test_update_folder_name_with_already_exists(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = dict(name="Night applets")

        response = await self.client.put(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731"),
            data,
        )

        assert response.status_code == 400, response.json()
        assert (
            response.json()["result"][0]["message"] == "Folder already exists."
        )

    @rollback
    async def test_delete_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307731")
        )
        assert response.status_code == 204, response.json()

    @rollback
    async def test_delete_not_belonging_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307733")
        )

        assert response.status_code == 403, response.json()
        assert response.json()["result"][0]["message"] == "Access denied."

    @rollback
    async def test_delete_not_empty_folder(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.detail_url.format(id="ecf66358-a717-41a7-8027-807374307732")
        )
        assert response.status_code == 400, response.json()
        assert (
            response.json()["result"][0]["message"]
            == "Folder has applets, move applets from folder to delete it."
        )

    @rollback
    async def test_pin_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307732",
                applet_id="190eb023-a610-403b-8d8e-b02c158c6f51",
            )
        )

        assert response.status_code == 200, response.json()

    @rollback
    async def test_unpin_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.pin_url.format(
                id="ecf66358-a717-41a7-8027-807374307732",
                applet_id="190eb023-a610-403b-8d8e-b02c158c6f51",
            )
        )

        assert response.status_code == 204, response.json()
