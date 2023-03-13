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
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.user_workspace_list)
        assert response.status_code == 200, response.json()

    @transaction.rollback
    async def test_workspace_applets_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.workspace_applets_list)
        assert response.status_code == 200

    @transaction.rollback
    async def test_workspace_remove_access(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        data = {
            "user_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "applet_ids": [
                "92917a56-d586-4613-b7aa-991f2c4b15b1",
            ],
        }

        response = await self.client.post(
            "/workspaces/removeAccess", data=data
        )

        assert response.status_code == 200
