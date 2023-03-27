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

    owner_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa2"
    login_url = "/auth/login"
    user_workspace_list = "/workspaces"
    workspace_applets_list = f"/workspaces/{owner_id}"
    remove_manager_access = f"{user_workspace_list}/removeAccess"
    remove_respondent_access = "/applets/removeAccess"

    @rollback
    async def test_user_workspace_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(self.user_workspace_list)
        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 2

    @rollback
    async def test_workspace_applets_list(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")

        response = await self.client.get(self.workspace_applets_list)
        assert response.status_code == 200
        assert response.json()["count"] == 1

    @transaction.rollback
    async def test_workspace_remove_manager_access(self):
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
            self.remove_manager_access, data=data
        )

        assert response.status_code == 200

    @transaction.rollback
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
