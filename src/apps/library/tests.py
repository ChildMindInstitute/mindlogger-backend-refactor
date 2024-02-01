import http
import uuid

import pytest

from apps.library.errors import (
    AppletNameExistsError,
    AppletVersionDoesNotExistError,
    AppletVersionExistsError,
    LibraryItemDoesNotExistError,
)
from apps.shared.test import BaseTest

APPLET_IN_LABRARY_NAME = "Applet 2"
APPLET_IN_LABRARY_ID = "92917a56-d586-4613-b7aa-991f2c4b15b2"
ID_DOES_NOT_EXIST = "00000000-0000-0000-0000-000000000000"
ACTIVITY_KEY = "577dbbda-3afc-4962-842b-8d8d11588bfe"


@pytest.fixture
def applet_data():
    return dict(
        display_name=APPLET_IN_LABRARY_NAME,
        encryption=dict(
            public_key=uuid.uuid4().hex,
            prime=uuid.uuid4().hex,
            base=uuid.uuid4().hex,
            account_id=str(uuid.uuid4()),
        ),
        description=dict(en="description"),
        activities=[
            dict(
                name="name",
                key=ACTIVITY_KEY,
                description=dict(en="description"),
                items=[
                    dict(
                        name="item1",
                        question=dict(en="question"),
                        response_type="message",
                        response_values=None,
                        config=dict(
                            remove_back_button=False,
                            timer=1,
                        ),
                    ),
                ],
            )
        ],
        activity_flows=[],
    )


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

    applet_expected_keys = {
        "about",
        "activities",
        "activityFlows",
        "description",
        "displayName",
        "id",
        "image",
        "keywords",
        "themeId",
        "version",
    }

    async def test_library_share(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2"]

    async def test_library_check_name(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(name="PHQ2")
        response = await client.post(self.library_check_name_url, data=data)
        assert response.status_code == http.HTTPStatus.OK

    async def test_library_get_all_search(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.library_url)
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert len(result) == 2
        assert result[1]["keywords"] == ["test", "test2"]

        assert set(result[0].keys()) == self.applet_expected_keys

        response = await client.get(
            self.library_url_search.format(search_term="test")
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert len(result) == 1

    async def test_library_get_detail(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        result = response.json()["result"]

        response = await client.get(
            self.library_detail_url.format(library_id=result["id"])
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert set(result.keys()) == self.applet_expected_keys
        assert result["keywords"] == ["test", "test2"]

    async def test_library_get_url(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(
            self.applet_link.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert isinstance(result["url"], str)

    async def test_library_update(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        result = response.json()["result"]

        data = dict(
            keywords=["test", "test2", "test3"],
            name="PHQ23",
        )

        response = await client.put(
            self.library_detail_url.format(library_id=result["id"]), data=data
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2", "test3"]

    async def test_add_to_cart(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            cart_items=[
                dict(
                    id="92917a56-d586-4613-b7aa-991f2c4b15b2",
                    display_name="Applet 2",
                    description={"en": "Patient Health Questionnaire"},
                    about={"en": "Patient Health Questionnaire"},
                    image="",
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
        response = await client.post(self.library_cart_url, data=create_data)
        assert response.status_code == http.HTTPStatus.OK, response.json()

        result = response.json()["result"]

        assert len(result["cartItems"]) == 1
        assert (
            result["cartItems"][0]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b2"
        )

        response = await client.get(self.library_cart_url)

        assert response.status_code == http.HTTPStatus.OK, response.json()

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
    async def test_cart_search(self, client, search, expected, page, limit):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        create_data = dict(
            cart_items=[
                dict(
                    id="92917a56-d586-4613-b7aa-991f2c4b15b3",
                    display_name="Applet 3",
                    description={"en": "Patient Health Questionnaire"},
                    about={"en": "Patient Health Questionnaire"},
                    image="",
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
                        )
                    ],
                    activity_flows=None,
                ),
            ]
        )
        response = await client.post(self.library_cart_url, data=create_data)
        assert response.status_code == http.HTTPStatus.OK
        response = await client.get(
            self.library_cart_url,
            query={"search": search, "page": page, "limit": limit},
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"][0]["id"] == expected
        assert len(response.json()["result"]) <= limit

    async def test_library_list_data_integrity(self, client):
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id=applet_id,
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.library_url)
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert len(result) == 2
        applet = next(
            filter(lambda item: item["displayName"] == "PHQ2", result), None
        )
        assert applet
        assert set(applet.keys()) == self.applet_expected_keys
        assert applet["description"] == {"en": "Patient Health Questionnaire"}
        assert applet["about"] == {"en": "Patient Health Questionnaire"}
        assert applet["keywords"] == ["test", "test2"]
        assert applet["version"] == "1.0.0"
        assert applet["image"] == "image_url"
        assert len(applet["activities"]) == 2

    async def test_library_slider_values(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.library_url,
            data=dict(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                keywords=["MyApplet"],
                name="MyAppletName",
            ),
        )
        assert response.status_code == http.HTTPStatus.CREATED
        assert response.json().get("result")
        result = response.json().get("result")
        response = await client.get(
            self.library_detail_url.format(library_id=result.get("id"))
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json().get("result")
        applet = response.json().get("result")

        items = applet["activities"][0]["items"]
        slider_responses = next(
            filter(lambda i: i["responseType"] == "slider", items), None
        )
        assert slider_responses.get("responseValues")

    async def test_library_check_activity_item_config_fields(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.library_url)
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        config: dict = result[0]["activities"][0]["items"][0]["config"]
        for key, value in config.items():
            assert key.find("_") == -1
            if isinstance(value, dict):
                for key_inner in value:
                    assert key_inner.find("_") == -1

    async def test_library_applet_name_already_exists(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(name=APPLET_IN_LABRARY_NAME)
        response = await client.post(self.library_check_name_url, data=data)

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        res = response.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletNameExistsError.message

    async def test_library_share_version_exists(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = dict(
            applet_id=APPLET_IN_LABRARY_ID,
            keywords=[],
            name=APPLET_IN_LABRARY_ID + "new",
        )
        response = await client.post(self.library_url, data=data)

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        res = response.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletVersionExistsError.message

    async def test_library_update_library_does_not_exist(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        data = dict(
            keywords=["test", "test2", "test3"],
            name="PHQ23",
        )

        resp = await client.put(
            self.library_detail_url.format(library_id=ID_DOES_NOT_EXIST),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == LibraryItemDoesNotExistError.message

    async def test_get_cart_no_cart_for_user(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        resp = await client.get(self.library_cart_url)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]
        assert resp.json()["count"] == 0

    async def test_add_to_cart_no_cart_items(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(cart_items=[])
        resp = await client.post(self.library_cart_url, data=create_data)
        assert resp.status_code == http.HTTPStatus.OK
        # Check explicit that is None, because the None is used in the service
        # for empty list
        assert resp.json()["result"]["cartItems"] is None

    async def test_get_library_by_id_with_flows(
        self, client, applet_data
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        exp_activity_flow_name = "flow"
        applet_data["activity_flows"] = [
            dict(
                name=exp_activity_flow_name,
                description=dict(en="fl", fr="fl"),
                items=[dict(activity_key=ACTIVITY_KEY)],
            )
        ]
        # Update applet, change version
        resp = await client.put(
            f"/applets/{APPLET_IN_LABRARY_ID}", data=applet_data
        )
        assert resp.status_code == http.HTTPStatus.OK
        # Add new version to the library
        data = dict(
            applet_id=APPLET_IN_LABRARY_ID,
            keywords=[],
            name=APPLET_IN_LABRARY_NAME + "NEW",
        )
        resp = await client.post(self.library_url, data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        library_id = resp.json()["result"]["id"]
        # get library
        resp = await client.get(
            self.library_detail_url.format(library_id=library_id)
        )
        assert resp.status_code == http.HTTPStatus.OK
        activity_flwo = resp.json()["result"]["activityFlows"][0]
        assert activity_flwo["name"] == exp_activity_flow_name

    async def test_get_library_item_by_lib_id_library_does_not_exist(
        self, client, applet_data
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        # Update applet, change version
        resp = await client.put(
            f"/applets/{APPLET_IN_LABRARY_ID}", data=applet_data
        )
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.get(
            self.library_detail_url.format(library_id=ID_DOES_NOT_EXIST)
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == LibraryItemDoesNotExistError.message

    async def test_library_get_url_applet_version_does_not_exists(
        self, client, applet_data
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        # Update applet, change version
        resp = await client.put(
            f"/applets/{APPLET_IN_LABRARY_ID}", data=applet_data
        )
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.get(
            self.applet_link.format(applet_id=APPLET_IN_LABRARY_ID)
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletVersionDoesNotExistError.message
