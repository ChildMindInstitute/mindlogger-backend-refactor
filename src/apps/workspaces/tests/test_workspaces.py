import uuid

import pytest

from apps.shared.test import BaseTest
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import AppletAccessDenied, InvalidAppletIDFilter


class TestWorkspaces(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
        "schedule/fixtures/periodicity.json",
        "schedule/fixtures/events.json",
        "schedule/fixtures/activity_events.json",
        "schedule/fixtures/flow_events.json",
        "schedule/fixtures/user_events.json",
        "folders/fixtures/folders_applet.json",
        "subjects/fixtures/subjects.json",
    ]

    login_url = "/auth/login"
    workspaces_list_url = "/workspaces"
    workspaces_detail_url = f"{workspaces_list_url}/{{owner_id}}"
    workspaces_priority_role_url = f"{workspaces_detail_url}/priority_role"
    workspace_roles_url = f"{workspaces_detail_url}/roles"

    workspace_applets_url = f"{workspaces_detail_url}/applets"
    search_workspace_applets_url = f"{workspace_applets_url}/search/{{text}}"
    workspace_folder_applets_url = (
        f"{workspaces_detail_url}/folders/{{folder_id}}/applets"
    )

    workspace_applets_detail_url = f"{workspace_applets_url}/{{applet_id}}"
    applet_respondent_url = (
        f"{workspace_applets_detail_url}/respondents/{{respondent_id}}"
    )
    workspace_respondents_url = f"{workspaces_detail_url}/respondents"
    workspace_applet_respondents_list = (
        "/workspaces/{owner_id}/applets/{applet_id}/respondents"
    )
    workspace_respondent_applet_accesses = (
        f"{workspace_respondents_url}/{{respondent_id}}/accesses"
    )
    workspace_managers_url = f"{workspaces_detail_url}/managers"
    workspace_applet_managers_list = (
        "/workspaces/{owner_id}/applets/{applet_id}/managers"
    )
    workspace_manager_accesses_url = (
        f"{workspace_managers_url}/{{manager_id}}/accesses"
    )
    remove_manager_access = f"{workspaces_list_url}/managers/removeAccess"
    remove_respondent_access = "/applets/respondent/removeAccess"
    workspace_respondents_pin = (
        "/workspaces/{owner_id}/respondents/{user_id}/pin"
    )
    workspace_managers_pin = "/workspaces/{owner_id}/managers/{user_id}/pin"
    workspace_get_applet_respondent = (
        "/workspaces/{owner_id}"
        "/applets/{applet_id}"
        "/respondents/{respondent_id}"
    )

    async def test_user_workspace_list(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2

    async def test_user_workspace_list_super_admin(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(self.workspaces_list_url)
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2

    async def test_user_workspace_retrieve_without_managers(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(
            self.workspaces_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Lucy Gabel Test"
        assert response.json()["result"]["hasManagers"] is False

    async def test_get_users_priority_role_in_workspace(self, client):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")

        response = await client.get(
            self.workspaces_priority_role_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.COORDINATOR

    async def test_get_users_priority_role_in_workspace_super_admin(
        self, client
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspaces_priority_role_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["role"] == Role.SUPER_ADMIN

    async def test_workspace_roles_retrieve(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(
            self.workspace_roles_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        roles = data.get("92917a56-d586-4613-b7aa-991f2c4b15b1", [])
        assert roles == [Role.MANAGER, Role.RESPONDENT]

    async def test_workspace_roles_with_super_admin_retrieve(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspace_roles_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        roles = data.get("92917a56-d586-4613-b7aa-991f2c4b15b1", [])
        assert roles == [Role.OWNER, Role.SUPER_ADMIN, Role.RESPONDENT]

    async def test_user_workspace_retrieve_with_managers(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspaces_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Tom Isaak Test"
        assert response.json()["result"]["hasManagers"] is True

    async def test_user_workspace_retrieve_without_access(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspaces_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 403, response.json()

    async def test_workspace_applets_list(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(
            self.workspace_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            ),
            dict(ordering="-displayName,created_at"),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 3
        assert response.json()["result"][0]["type"] == "folder"
        assert response.json()["result"][1]["type"] == "folder"
        assert response.json()["result"][2]["type"] == "applet"
        assert response.json()["result"][2]["role"] == Role.OWNER

    async def test_workspace_applets_search(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(
            self.search_workspace_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2", text="applet"
            )
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["displayName"] == "Applet 3"
        assert response.json()["result"][0]["role"] == Role.OWNER

    async def test_workspace_applets_list_by_folder_id_filter(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspace_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 5

    async def test_workspace_applets_detail(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        # check access not exists
        response = await client.get(
            self.workspace_applets_detail_url.format(
                owner_id=uuid.uuid4(),
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )
        assert response.status_code == 404

        response = await client.get(
            self.workspace_applets_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )
        assert response.status_code == 200

    @pytest.mark.skip("Skip until M2-4890 will be done")
    async def test_workspace_applets_respondent_update(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.post(
            self.applet_respondent_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            ),
            dict(
                nickname="New respondent",
                secret_user_id="f0dd4996-e0eb-461f-b2f8-ba873a674710",
            ),
        )
        assert response.status_code == 200

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
            dict(
                role="respondent",
            ),
        )
        payload = response.json()
        assert payload["count"] == 4
        nicknames = []
        secret_ids = []
        for respondent in payload["result"]:
            nicknames += respondent.get("nicknames", [])
            secret_ids += respondent.get("secretIds", [])
        assert "New respondent" in nicknames
        assert "f0dd4996-e0eb-461f-b2f8-ba873a674710" in secret_ids

    async def test_wrong_workspace_applets_list(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await client.get(
            self.workspace_applets_url.format(
                owner_id="00000000-0000-0000-0000-000000000000"
            )
        )
        assert response.status_code == 404

    async def test_get_workspace_respondents(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_respondents_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 5
        assert data["result"][0]["nicknames"]
        assert data["result"][0]["secretIds"]

        # test search
        search_params = {
            "f0dd4996-e0eb-461f-b2f8-ba873a674788": [
                "b2f8-ba873a674788",
            ],
            "f0dd4996-e0eb-461f-b2f8-ba873a674789": [
                "f0dd4996-e0eb-461f-b2f8-ba873a674789",
            ],
        }
        for access_id, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_respondents_url.format(
                        owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
                    ),
                    dict(search=val),
                )
                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                access_ids = {
                    detail["accessId"] for detail in result[0]["details"]
                }
                assert access_id in access_ids

    async def test_get_workspace_applet_respondents(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 4
        assert data["result"][0]["nicknames"]
        assert data["result"][0]["secretIds"]

        # test search
        search_params = {
            "f0dd4996-e0eb-461f-b2f8-ba873a674788": [
                # "jane",
                "b2f8-ba873a674788",
            ],
            "f0dd4996-e0eb-461f-b2f8-ba873a674789": [
                # "john",
                "f0dd4996-e0eb-461f-b2f8-ba873a674789",
            ],
        }
        for access_id, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_applet_respondents_list.format(
                        owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                    ),
                    dict(search=val),
                )
                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                access_ids = {
                    detail["accessId"] for detail in result[0]["details"]
                }
                assert access_id in access_ids

    async def test_get_workspace_respondent_accesses(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_respondent_applet_accesses.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_get_workspace_managers(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_managers_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 6

        plain_emails = [
            "reviewer@mail.com",
            "tom@mindlogger.com",
            "lucy@gmail.com",
            "bob@gmail.com",
            "mike@gmail.com",
            "mike2@gmail.com",
        ]

        for result in response.json()["result"]:
            assert result["email"] in plain_emails

        # test search
        search_params = {
            "7484f34a-3acc-4ee6-8a94-fd7299502fa2": [
                "lucy",
                "gabe",
            ],
        }
        for id_, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_managers_url.format(
                        owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
                    ),
                    dict(
                        search=val,
                    ),
                )

                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_

    async def test_get_workspace_applet_managers(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 6

        plain_emails = [
            "reviewer@mail.com",
            "tom@mindlogger.com",
            "lucy@gmail.com",
            "bob@gmail.com",
            "mike@gmail.com",
            "mike2@gmail.com",
        ]

        for result in response.json()["result"]:
            assert result["email"] in plain_emails

        # test search
        search_params = {
            "7484f34a-3acc-4ee6-8a94-fd7299502fa2": [
                "lucy",
                "gabe",
            ],
        }
        for id_, params in search_params.items():
            for val in params:
                response = await client.get(
                    self.workspace_applet_managers_list.format(
                        owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                    ),
                    dict(
                        search=val,
                    ),
                )

                assert response.status_code == 200
                data = response.json()
                assert set(data.keys()) == {"count", "result"}
                assert data["count"] == 1
                result = data["result"]
                assert len(result) == 1
                assert result[0]["id"] == id_
                assert result[0]["firstName"] == "Lucy"
                assert result[0]["lastName"] == "Gabel"
                assert result[0]["email"] == "lucy@gmail.com"

    async def test_set_workspace_manager_accesses(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.workspace_manager_accesses_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                manager_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            ),
            dict(
                accesses=[
                    {
                        "applet_id": "92917a56-d586-4613-b7aa-991f2c4b15b4",
                        "roles": ["manager", "coordinator"],
                    },
                    {
                        "applet_id": "92917a56-d586-4613-b7aa-991f2c4b15b1",
                        "roles": ["coordinator", "editor", "reviewer"],
                        "respondents": [
                            "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                            "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
                        ],
                    },
                ]
            ),
        )

        assert response.status_code == 200, response.json()
        # TODO: check from database results

    @pytest.mark.skip("Skip until M2-4890 will be done")
    async def test_pin_workspace_respondents(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()

        user_id = response.json()["result"][-1]["id"]

        # Pin access wrong owner
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id=uuid.uuid4(), user_id=user_id
            ),
        )

        assert response.status_code == 404

        # Pin access wrong access_id
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=uuid.uuid4(),
            ),
        )

        assert response.status_code == 403

        # Pin access
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        assert response.json()["result"][0]["id"] == user_id
        assert response.json()["result"][0]["isPinned"] is True
        assert response.json()["result"][1]["isPinned"] is False

        # Unpin access
        response = await client.post(
            self.workspace_respondents_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        assert response.json()["result"][-1]["id"] == user_id

    async def test_pin_workspace_managers(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200, response.json()

        user_id = response.json()["result"][-1]["id"]

        # Pin access wrong owner
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id=uuid.uuid4(), user_id=user_id
            ),
        )

        assert response.status_code == 404

        # Pin access wrong access_id
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=uuid.uuid4(),
            ),
        )

        assert response.status_code == 403

        # Pin access
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        assert response.json()["result"][0]["id"] == user_id
        assert response.json()["result"][0]["isPinned"] is True
        assert response.json()["result"][1]["isPinned"] is False

        # Unpin access
        response = await client.post(
            self.workspace_managers_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                user_id=user_id,
            ),
        )

        assert response.status_code == 204

        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )
        assert response.json()["result"][-1]["id"] == user_id

    async def test_workspace_remove_manager_access(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(
            self.workspace_managers_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )

        assert response.status_code == 200

        managers_count = response.json()["count"]

        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
            # "role": Role.MANAGER,
        }

        response = await client.delete(self.remove_manager_access, data=data)

        assert response.status_code == 200

        response = await client.get(
            self.workspace_managers_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == managers_count - 1

    async def test_workspace_remove_respondent_access(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
            "delete_responses": True,
        }

        response = await client.delete(
            self.remove_respondent_access, data=data
        )
        assert response.status_code == 200

    async def test_workspace_coordinator_remove_respondent_access(
        self, client
    ):
        # coordinator can remove respondent access
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")

        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
            "delete_responses": True,
        }

        response = await client.delete(
            self.remove_respondent_access, data=data
        )
        assert response.status_code == 200

    async def test_workspace_editor_remove_respondent_access_error(
        self, client
    ):
        # editor can remove respondent access
        await client.login(self.login_url, "mike2@gmail.com", "Test1234")

        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
            "delete_responses": True,
        }

        response = await client.delete(
            self.remove_respondent_access, data=data
        )
        assert response.status_code == 403

    async def test_folder_applets(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspace_folder_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                folder_id="ecf66358-a717-41a7-8027-807374307732",
            )
        )
        assert response.status_code == 200
        assert response.json()["result"][0]["displayName"] == "Applet 1"
        assert response.json()["result"][1]["displayName"] == "Applet 2"

    async def test_folder_applets_not_super_admin(self, client):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")

        response = await client.get(
            self.workspace_folder_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa3",
                folder_id="ecf66358-a717-41a7-8027-807374307737",
            )
        )
        assert response.status_code == 200
        assert len(response.json()["result"]) == 1
        assert response.json()["result"][0]["displayName"] == "Applet 4"

    async def test_applets_with_description(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.workspace_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            )
        )
        assert response.status_code == 200
        applets = response.json()["result"]
        assert applets[3]["activityCount"] == 1
        assert applets[3]["description"] == {
            "en": "Patient Health Questionnaire"
        }

    async def test_applets_flat_list(self, client):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.get(
            self.workspace_applets_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            ),
            dict(ordering="-displayName,created_at", flatList=True),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["type"] == "applet"

    async def test_applet_get_respondent_success(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        url = self.workspace_get_applet_respondent.format(
            owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2",
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
        )
        res = await client.get(url)
        assert res.status_code == 200
        body = res.json()
        respondent = body.get("result", {})
        assert len(respondent) == 2
        # encrypted "hFywashKw+KlcDPazIy5QHz4AdkTOYkD28Q8+dpeDDA=" nickname
        # is 'Mindlogger ChildMindInstitute'
        assert respondent["nickname"] == "Mindlogger ChildMindInstitute"
        assert respondent["secretUserId"] == (
            "f0dd4996-e0eb-461f-b2f8-ba873a674782"
        )

    async def test_applet_get_respondent_not_found(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        url = self.workspace_get_applet_respondent.format(
            owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2",
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 404

    async def test_applet_get_respondent_access_denied_for_respondent_role(
        self, client
    ):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")
        url = self.workspace_get_applet_respondent.format(
            owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            applet_id="92917a56-d586-4613-b7aa-991f2c4b15b2",
            respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa0",
        )
        res = await client.get(url)
        assert res.status_code == 403

    async def test_get_managers_priority_roles_not_valid_uuid(self, client):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")
        response = await client.get(
            self.workspaces_priority_role_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            query={"appletIDs": "92917a56"},
        )
        assert response.status_code == 422
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == InvalidAppletIDFilter.message

    async def test_get_managers_priority_roles_user_does_not_have_access_to_the_applet(  # noqa: E501
        self, client
    ):
        await client.login(self.login_url, "bob@gmail.com", "Test1234!")
        response = await client.get(
            self.workspaces_priority_role_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            query={"appletIDs": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 403
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletAccessDenied.message
