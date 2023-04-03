import pytest

from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestWorkspaces(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    user_workspace_list = "/workspaces"
    workspace_applets_list = "/workspaces/{owner_id}/applets"
    workspace_users_list = "/workspaces/{owner_id}/users"
    workspace_users_pin = "/workspaces/{owner_id}/users/pin"

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
    async def test_workspace_applets_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(
            self.workspace_applets_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2"
            )
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

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
    async def test_get_workspace_users(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_users_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 4
        assert len(response.json()["result"][0]["nickname"]) > 1

    @pytest.mark.main
    @rollback
    async def test_pin_workspace_users(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.workspace_users_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )

        assert response.status_code == 200, response.json()

        access_id = response.json()["result"][-1]["accessId"]
        # Pin access
        response = await self.client.post(
            self.workspace_users_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=dict(access_id=access_id),
        )

        assert response.status_code == 200

        response = await self.client.get(
            self.workspace_users_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.json()["result"][0]["accessId"] == access_id

        # Unpin access
        response = await self.client.post(
            self.workspace_users_pin.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=dict(access_id=access_id),
        )

        assert response.status_code == 200

        response = await self.client.get(
            self.workspace_users_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            )
        )
        assert response.json()["result"][-1]["accessId"] == access_id
