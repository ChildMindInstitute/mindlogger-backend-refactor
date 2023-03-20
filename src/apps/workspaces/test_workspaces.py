from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestWorkspaces(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "invitations/fixtures/invitations.json",
        "workspaces/fixtures/workspaces.json",
    ]

    owner_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa2"
    login_url = "/auth/login"
    user_workspace_list = "/workspaces"
    workspace_applets_list = f"/workspaces/{owner_id}"

    @transaction.rollback
    async def test_user_workspace_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(self.user_workspace_list)
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2

    @transaction.rollback
    async def test_workspace_applets_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(self.workspace_applets_list)
        assert response.status_code == 200
        assert response.json()["count"] == 1
