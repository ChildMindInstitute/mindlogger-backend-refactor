from apps.shared.test import BaseTest


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

    async def test_user_workspace_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.user_workspace_list)
        assert response.status_code == 200
