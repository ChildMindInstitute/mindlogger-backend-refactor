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
        "activities/fixtures/activity_histories.json",
        "activities/fixtures/activity_item_histories.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
        "library/fixtures/libraries.json",
    ]

    login_url = "/auth/login"
    library_url = "/library"
    library_url_search = "/library?search={search_term}"
    library_check_name_url = "/library/check_name"
    library_detail_url = f"{library_url}/{{library_id}}"
    library_cart_url = f"{library_url}/cart"

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
        assert len(result) == 2
        assert result[1]["keywords"] == ["test", "test2"]

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
        assert type(result["url"]) == str

    @rollback
    async def test_library_update(self):
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

        data = dict(
            keywords=["test", "test2", "test3"],
            name="PHQ23",
        )

        response = await self.client.put(
            self.library_detail_url.format(library_id=result["id"]), data=data
        )
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2", "test3"]

    @rollback
    async def test_add_to_cart(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            cart_items=[
                dict(
                    library_id="68aadd6c-eb20-4666-85aa-fd6264825c01",
                    activities=[
                        dict(
                            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3612",
                            items=None,
                        )
                    ],
                ),
            ]
        )
        response = await self.client.post(
            self.library_cart_url, data=create_data
        )
        assert response.status_code == 200, response.json()

        result = response.json()["result"]

        assert len(result["cartItems"]) == 1
        assert (
            result["cartItems"][0]["libraryId"]
            == "68aadd6c-eb20-4666-85aa-fd6264825c01"
        )

        response = await self.client.get(self.library_cart_url)

        assert response.status_code == 200, response.json()

        result = response.json()["result"]
        assert len(result["cartItems"]) == 1
        assert (
            result["cartItems"][0]["libraryId"]
            == "68aadd6c-eb20-4666-85aa-fd6264825c01"
        )
