import pytest

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
                    id="92917a56-d586-4613-b7aa-991f2c4b15b2",
                    display_name="Applet 2",
                    description={"en": "Patient Health Questionnaire"},
                    about={"en": "Patient Health Questionnaire"},
                    image="",
                    watermark="",
                    theme_id="3e31a64e-449f-4788-8516-eca7809f1a42",
                    version="2.0.1",
                    activities=[
                        dict(
                            key="09e3dbf0-aefb-4d0e-9177-bdb321bf3612",
                            items=None,
                            name="PHQ8",
                            description={"en": "PHQ8", "fr": "PHQ8"},
                            splash_screen="",
                            image="",
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
            result["cartItems"][0]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b2"
        )

        response = await self.client.get(self.library_cart_url)

        assert response.status_code == 200, response.json()

        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["id"] == "92917a56-d586-4613-b7aa-991f2c4b15b2"

    @pytest.mark.parametrize(
        "search,expected,page,limit",
        (
            ("3", "92917a56-d586-4613-b7aa-991f2c4b15b3", 1, 10),
            ("4", "92917a56-d586-4613-b7aa-991f2c4b15b4", 1, 10),
            ("One", "92917a56-d586-4613-b7aa-991f2c4b15b3", 1, 10),
            ("Two", "92917a56-d586-4613-b7aa-991f2c4b15b3", 1, 10),
            ("Three", "92917a56-d586-4613-b7aa-991f2c4b15b4", 1, 10),
            ("Four", "92917a56-d586-4613-b7aa-991f2c4b15b4", 1, 10),
            ("PHQ9", "92917a56-d586-4613-b7aa-991f2c4b15b4", 1, 10),
            ("AMQ", "92917a56-d586-4613-b7aa-991f2c4b15b3", 1, 10),
            ("Applet", "92917a56-d586-4613-b7aa-991f2c4b15b3", 1, 1),
            ("Applet", "92917a56-d586-4613-b7aa-991f2c4b15b4", 2, 1),
        ),
    )
    @rollback
    async def test_cart_search(self, search, expected, page, limit):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            cart_items=[
                dict(
                    id="92917a56-d586-4613-b7aa-991f2c4b15b3",
                    display_name="Applet 3",
                    description={"en": "Patient Health Questionnaire"},
                    about={"en": "Patient Health Questionnaire"},
                    image="",
                    watermark="",
                    theme_id=None,
                    keywords=["One", "Two"],
                    version="1.0",
                    activities=[
                        dict(
                            key="09e3dbf0-aefb-4d0e-9177-bdb321bf3613",
                            items=None,
                            name="AMQ",
                            description={"en": "PHQ9", "fr": "PHQ9"},
                            splash_screen="",
                            image="",
                        )
                    ],
                    activity_flows=None,
                ),
                dict(
                    id="92917a56-d586-4613-b7aa-991f2c4b15b4",
                    display_name="Applet 4",
                    description={"en": "Patient Health Questionnaire"},
                    image="",
                    watermark="",
                    theme_id=None,
                    keywords=["Three", "Four"],
                    version="1.0",
                    activities=[
                        dict(
                            key="09e3dbf0-aefb-4d0e-9177-bdb321bf3614",
                            name="PHQ9",
                            description={"en": "PHQ9", "fr": "PHQ9"},
                            image="",
                            splash_screen="",
                            items=None,
                        ),
                        dict(
                            key="494544c9-e7f1-4d7b-8eea-4ddc840c25fc",
                            items=None,
                            name="PHQ9",
                            description={"en": "PHQ9", "fr": "PHQ9"},
                            splash_screen="",
                            image="",
                        ),
                    ],
                    activity_flows=None,
                ),
            ]
        )
        response = await self.client.post(
            self.library_cart_url, data=create_data
        )
        assert response.status_code == 200
        response = await self.client.get(
            self.library_cart_url,
            query={"search": search, "page": page, "limit": limit},
        )
        assert response.status_code == 200
        assert response.json()["result"][0]["id"] == expected
        assert len(response.json()["result"]) <= limit

    @rollback
    async def test_library_list_data_integrity(self):
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = dict(
            applet_id=applet_id,
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await self.client.post(self.library_url, data=data)
        assert response.status_code == 201, response.json()

        response = await self.client.get(self.library_url)
        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert len(result) == 2
        applet = next(
            filter(lambda item: item["displayName"] == "PHQ2", result), None
        )
        assert applet
        assert applet["description"] == {"en": "Patient Health Questionnaire"}
        assert applet["about"] == {"en": "Patient Health Questionnaire"}
        assert applet["keywords"] == ["test", "test2"]
        assert applet["version"] == "1.0.0"
        assert len(applet["activities"]) == 2
