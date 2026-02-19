from apps.shared.test import BaseTest


class TestThemes(BaseTest):
    login_url = "/auth/login"
    list_url = "/themes"

    async def test_themes_list(self, client, tom):
        client.login(tom)
        response = await client.get(self.list_url)

        assert response.status_code == 200
        assert isinstance(response.json()["result"], list)
