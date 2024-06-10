import http
import uuid
from typing import Any

import pytest

from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.library.errors import (
    AppletNameExistsError,
    AppletVersionDoesNotExistError,
    AppletVersionExistsError,
    LibraryItemDoesNotExistError,
)
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User

DictStrAny = dict[str, Any]


@pytest.fixture
def applet_data(applet_two: AppletFull) -> DictStrAny:
    data = AppletUpdate(**applet_two.dict(exclude_none=True))
    return data.dict()


class TestLibrary(BaseTest):
    fixtures = [
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

    async def test_library_share(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2"]

    async def test_library_check_name(self, client, tom: User):
        client.login(tom)

        data = dict(name="PHQ2")
        response = await client.post(self.library_check_name_url, data=data)
        assert response.status_code == http.HTTPStatus.OK

    async def test_library_get_all_search(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
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

        response = await client.get(self.library_url_search.format(search_term="test"))
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert len(result) == 1

    async def test_library_get_detail(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        result = response.json()["result"]

        response = await client.get(self.library_detail_url.format(library_id=result["id"]))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert set(result.keys()) == self.applet_expected_keys
        assert result["keywords"] == ["test", "test2"]

    async def test_library_get_url(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
            keywords=["test", "test2"],
            name="PHQ2",
        )
        response = await client.post(self.library_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.applet_link.format(applet_id=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert isinstance(result["url"], str)

    async def test_library_update(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
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

        response = await client.put(self.library_detail_url.format(library_id=result["id"]), data=data)
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert result["keywords"] == ["test", "test2", "test3"]

    async def test_add_to_cart(self, client: TestClient, applet_two: AppletFull, tom: User):
        client.login(tom)

        create_data = dict(
            cart_items=[
                dict(
                    id=applet_two.id,
                    display_name=applet_two.display_name,
                    description={"en": "Patient Health Questionnaire"},
                    about={"en": "Patient Health Questionnaire"},
                    image=applet_two.image,
                    theme_id=applet_two.theme_id,
                    activities=[
                        dict(
                            key=applet_two.activities[0].key,
                            items=None,
                            name=applet_two.activities[0].name,
                            description=applet_two.activities[0].description,
                            splash_screen=applet_two.activities[0].splash_screen,
                            image=applet_two.activities[0].image,
                        )
                    ],
                    version=applet_two.version,
                ),
            ]
        )
        response = await client.post(self.library_cart_url, data=create_data)
        assert response.status_code == http.HTTPStatus.OK, response.json()

        result = response.json()["result"]

        assert len(result["cartItems"]) == 1
        assert result["cartItems"][0]["id"] == str(applet_two.id)

        response = await client.get(self.library_cart_url)

        assert response.status_code == http.HTTPStatus.OK, response.json()

        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["id"] == str(applet_two.id)

    @pytest.mark.parametrize(
        "search,applet_fixture_name,page,limit",
        (
            ("3", "applet_three", 1, 10),
            ("4", "applet_four", 1, 10),
            ("One", "applet_three", 1, 10),
            ("Two", "applet_three", 1, 10),
            ("Three", "applet_four", 1, 10),
            ("Four", "applet_four", 1, 10),
            ("PHQ9", "applet_four", 1, 10),
            ("AMQ", "applet_three", 1, 10),
            ("Applet", "applet_three", 1, 1),
            ("Applet", "applet_four", 2, 1),
        ),
    )
    async def test_cart_search(
        self, client, search, applet_fixture_name, page, limit, request, applet_three, applet_four, tom: User
    ):
        applet_fixture = request.getfixturevalue(applet_fixture_name)
        client.login(tom)

        create_data = dict(
            cart_items=[
                dict(
                    id=str(applet_three.id),
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
                    id=str(applet_four.id),
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
        assert response.json()["result"][0]["id"] == str(applet_fixture.id)
        assert len(response.json()["result"]) <= limit

    async def test_library_list_data_integrity(
        self, client: TestClient, applet_one: AppletFull, applet_two: AppletFull, tom: User
    ):
        applet_id = applet_one.id
        client.login(tom)

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
        applet = next(filter(lambda item: item["displayName"] == "PHQ2", result), None)
        assert applet
        assert set(applet.keys()) == self.applet_expected_keys
        assert applet["description"] == applet_two.description
        assert applet["about"] == applet_two.about
        assert applet["keywords"] == ["test", "test2"]
        assert applet["version"] == applet_two.version
        assert applet["image"] == applet_two.image
        assert len(applet["activities"]) == len(applet_two.activities)

    async def test_applet_in_library_item_with_response_values(
        self, client: TestClient, applet_one: AppletFull, tom: User
    ):
        client.login(tom)
        response = await client.post(
            self.library_url,
            data=dict(
                applet_id=applet_one.id,
                keywords=["MyApplet"],
                name="MyAppletName",
            ),
        )
        assert response.status_code == http.HTTPStatus.CREATED
        assert response.json().get("result")
        result = response.json().get("result")
        response = await client.get(self.library_detail_url.format(library_id=result.get("id")))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json().get("result")
        applet = response.json().get("result")

        item = applet["activities"][0]["items"][0]
        assert item["responseValues"]

    async def test_library_check_activity_item_config_fields(
        self, client: TestClient, applet_one: AppletFull, tom: User
    ):
        client.login(tom)

        data = dict(
            applet_id=applet_one.id,
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

    async def test_library_applet_name_already_exists(self, client: TestClient, applet_two: AppletFull, tom: User):
        client.login(tom)
        data = dict(name=applet_two.display_name)
        response = await client.post(self.library_check_name_url, data=data)

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        res = response.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletNameExistsError.message

    async def test_library_share_version_exists(self, client: TestClient, applet_two: AppletFull, tom: User):
        client.login(tom)
        data = dict(
            applet_id=applet_two.id,
            keywords=[],
            name=str(applet_two.id) + "new",
        )
        response = await client.post(self.library_url, data=data)

        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        res = response.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletVersionExistsError.message

    async def test_library_update_library_does_not_exist(self, client: TestClient, uuid_zero: uuid.UUID, tom: User):
        client.login(tom)

        data = dict(
            keywords=["test", "test2", "test3"],
            name="PHQ23",
        )

        resp = await client.put(
            self.library_detail_url.format(library_id=uuid_zero),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == LibraryItemDoesNotExistError.message

    @pytest.mark.usefixtures("applet_two")
    async def test_get_cart_no_cart_for_user(self, client: TestClient, tom: User):
        client.login(tom)
        resp = await client.get(self.library_cart_url)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]
        assert resp.json()["count"] == 0

    @pytest.mark.usefixtures("applet_two")
    async def test_add_to_cart_no_cart_items(self, client: TestClient, tom: User):
        client.login(tom)
        create_data: dict[str, list] = dict(cart_items=[])
        resp = await client.post(self.library_cart_url, data=create_data)
        assert resp.status_code == http.HTTPStatus.OK
        # Check explicit that is None, because the None is used in the service
        # for empty list
        assert resp.json()["result"]["cartItems"] is None

    async def test_get_library_by_id_with_flows(
        self, client: TestClient, applet_data: DictStrAny, applet_two: AppletFull, tom: User
    ) -> None:
        client.login(tom)
        exp_activity_flow_name = "flow"
        applet_data["activity_flows"] = [
            dict(
                name=exp_activity_flow_name,
                description=dict(en="fl", fr="fl"),
                items=[dict(activity_key=applet_two.activities[0].key)],
            )
        ]
        # Update applet, change version
        resp = await client.put(f"/applets/{applet_two.id}", data=applet_data)
        assert resp.status_code == http.HTTPStatus.OK
        # Add new version to the library
        data = dict(
            applet_id=applet_two.id,
            keywords=[],
            name=applet_two.display_name + "NEW",
        )
        resp = await client.post(self.library_url, data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        library_id = resp.json()["result"]["id"]
        # get library
        resp = await client.get(self.library_detail_url.format(library_id=library_id))
        assert resp.status_code == http.HTTPStatus.OK
        activity_flwo = resp.json()["result"]["activityFlows"][0]
        assert activity_flwo["name"] == exp_activity_flow_name

    async def test_get_library_item_by_lib_id_library_does_not_exist(
        self, client: TestClient, applet_data: DictStrAny, applet_two: AppletFull, uuid_zero: uuid.UUID, tom: User
    ) -> None:
        client.login(tom)
        # Update applet, change version
        resp = await client.put(f"/applets/{applet_two.id}", data=applet_data)
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.get(self.library_detail_url.format(library_id=uuid_zero))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == LibraryItemDoesNotExistError.message

    async def test_library_get_url_applet_version_does_not_exists(
        self, client: TestClient, applet_data: DictStrAny, applet_two: AppletFull, tom: User
    ) -> None:
        client.login(tom)
        # Update applet, change version
        resp = await client.put(f"/applets/{applet_two.id}", data=applet_data)
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.get(self.applet_link.format(applet_id=applet_two.id))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        res = resp.json()["result"]
        assert len(res) == 1
        assert res[0]["message"] == AppletVersionDoesNotExistError.message

    @pytest.mark.parametrize(
        "kw, exp_kw, exp_status, include_kw",
        (
            (["test", "test2"], ["test", "test2"], http.HTTPStatus.CREATED, True),
            ([], [], http.HTTPStatus.CREATED, True),
            (None, [], http.HTTPStatus.CREATED, False),
            (None, [], http.HTTPStatus.UNPROCESSABLE_ENTITY, True),
        ),
    )
    async def test_library_share_with_empty_kw(
        self, client: TestClient, applet_one: AppletFull, tom: User, kw, exp_kw, exp_status, include_kw
    ):
        client.login(tom)
        data = dict(applet_id=applet_one.id, name="PHQ2")
        if include_kw:
            data["keywords"] = kw

        response = await client.post(self.library_url, data=data)
        assert response.status_code == exp_status
        if exp_status == http.HTTPStatus.CREATED:
            result = response.json()["result"]
            assert result["keywords"] == exp_kw
