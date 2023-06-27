from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestLibrary(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "themes/fixtures/themes.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_histories.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
    ]

    login_url = "/auth/login"
    library_url = "/library"
    library_url_search = "/library?search={search_term}"
    library_check_name_url = "/library/check_name"
    library_detail_url = f"{library_url}/{{library_id}}"

    applet_link = "/applets/{applet_id}/library_link"

    @rollback
    async def test_library_share(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await self.client.post(self.library_url, data=data)

        assert response.status_code == 201, response.json()
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2"]

    @rollback
    async def test_library_check_name(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            name="PHQ2",
        )
        response = await self.client.post(
            self.library_check_name_url, data=data
        )

        assert response.status_code == 200, response.json()

    @rollback
    async def test_library_get_all_search(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await self.client.post(self.library_url, data=data)
        assert response.status_code == 201, response.json()

        response = await self.client.get(self.library_url)
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["keywords"] == ["test", "test2"]

        response = await self.client.get(
            self.library_url_search.format(search_term="test")
        )
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert len(result) == 1

    @rollback
    async def test_library_get_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await self.client.post(self.library_url, data=data)
        assert response.status_code == 201, response.json()
        result = response.json()["result"]

        response = await self.client.get(
            self.library_detail_url.format(library_id=result["id"])
        )

        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2"]

    @rollback
    async def test_library_get_url(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await self.client.post(self.library_url, data=data)
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_link.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert type(result) == str
