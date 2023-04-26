from uuid import uuid4

from apps.shared.test import BaseTest
from apps.workspaces.domain.constants import Role
from infrastructure.database import rollback


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
    ]

    login_url = "/auth/login"
    user_workspace_list = "/workspaces"
    user_workspace_detail = "/workspaces/{owner_id}"
    workspace_applets_list = "/workspaces/{owner_id}/applets"
    workspace_applets_detail = "/workspaces/{owner_id}/applets/{id_}"
    workspace_respondents_list = "/workspaces/{owner_id}/respondents"
    workspace_respondent_applet_accesses = (
        "/workspaces/{owner_id}/respondents/{respondent_id}/accesses"
    )
    workspace_managers_list = "/workspaces/{owner_id}/managers"
    remove_manager_access = "/workspaces/removeAccess"
    remove_respondent_access = "/applets/removeAccess"
    workspace_respondents_pin = "/workspaces/{owner_id}/respondents/pin"

    @rollback
    async def test_user_workspace_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.user_workspace_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2

    @rollback
    async def test_user_workspace_retrieve_without_managers(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.user_workspace_detail.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Lucy Gabel Test"
        assert response.json()["result"]["hasManagers"] is False

    @rollback
    async def test_user_workspace_retrieve_with_managers(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.user_workspace_detail.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.status_code == 200, response.json()
        assert response.json()["result"]["name"] == "Tom Isaak Test"
        assert response.json()["result"]["hasManagers"] is True

    @rollback
    async def test_user_workspace_retrieve_without_access(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.user_workspace_detail.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 403, response.json()

    @rollback
    async def test_workspace_applets_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.workspace_applets_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["role"] == Role.ADMIN

    @rollback
    async def test_workspace_applets_detail(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        # check access not exists
        response = await self.client.get(
            self.workspace_applets_detail.format(
                owner_id=uuid4(),
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )
        assert response.status_code == 404

        response = await self.client.get(
            self.workspace_applets_detail.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
                id_="92917a56-d586-4613-b7aa-991f2c4b15b1",
            )
        )
        assert response.status_code == 200

    @rollback
    async def test_wrong_workspace_applets_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.workspace_applets_list.format(
                owner_id="00000000-0000-0000-0000-000000000000"
            )
        )
        # todo: uncomment when it will be needed
        # assert response.status_code == 404
        assert response.status_code == 200

    @rollback
    async def test_get_workspace_respondents(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 2
        assert len(response.json()["result"][0]["nickname"]) > 1
        assert response.json()["result"][0]["role"] == Role.RESPONDENT
        assert response.json()["result"][1]["role"] == Role.RESPONDENT

    @rollback
    async def test_get_workspace_respondent_accesses(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_respondent_applet_accesses.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    @rollback
    async def test_get_workspace_managers(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 4

    @rollback
    async def test_pin_workspace_users(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )

        assert response.status_code == 200, response.json()

        access_id = response.json()["result"][-1]["accessId"]
        # Pin access
        response = await self.client.post(
            self.workspace_respondents_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=dict(access_id=access_id),
        )

        assert response.status_code == 200

        response = await self.client.get(
            self.workspace_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert response.json()["result"][0]["accessId"] == access_id

        # Unpin access
        response = await self.client.post(
            self.workspace_respondents_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=dict(access_id=access_id),
        )

        assert response.status_code == 200

        response = await self.client.get(
            self.workspace_respondents_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            dict(appletId="92917a56-d586-4613-b7aa-991f2c4b15b1"),
        )
        assert response.json()["result"][-1]["accessId"] == access_id

    @rollback
    async def test_workspace_remove_manager_access(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_managers_list.format(
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
        }

        response = await self.client.post(
            self.remove_manager_access, data=data
        )

        assert response.status_code == 200

        response = await self.client.get(
            self.workspace_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == managers_count - 1

    @rollback
    async def test_workspace_remove_respondent_access(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
            "delete_responses": True,
        }

        response = await self.client.post(
            self.remove_respondent_access, data=data
        )
        assert response.status_code == 200
