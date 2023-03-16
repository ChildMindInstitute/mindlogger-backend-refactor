from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestData(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
    ]

    login_url = "/auth/login"
    generating_url = "/data"
    generate_applet_url = f"{generating_url}/generate_applet"
    applet_list_url = "applets"

    @transaction.rollback
    async def test_generate_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(self.generate_applet_url)

        assert response.status_code == 201, response.json()
        response = await self.client.get(self.applet_list_url)
        assert response.status_code == 200
        assert response.json()["count"] == 1
