from pydantic.color import Color

from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestThemes(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/login"
    list_url = "/themes"
    detail_url = "themes/{id}"

    @transaction.rollback
    async def test_create_theme(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await self.client.post(self.list_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"] == 1

    @transaction.rollback
    async def test_delete_theme(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await self.client.post(self.list_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"] == 1

        response = await self.client.delete(self.detail_url.format(id=1))

        assert response.status_code == 204, response.json()

    @transaction.rollback
    async def test_update_theme(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await self.client.post(self.list_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"] == 1

        update_data = dict(
            name="Test theme 2",
            logo="test/logo2.png",
            background_image="test/background2.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )
        response = await self.client.put(
            self.detail_url.format(id=1), data=update_data
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["id"] == 1
        assert response.json()["result"]["name"] == update_data["name"]
        assert response.json()["result"]["logo"] == update_data["logo"]
        assert (
            response.json()["result"]["backgroundImage"]
            == update_data["background_image"]
        )
        assert (
            response.json()["result"]["primaryColor"]
            == Color(update_data["primary_color"]).as_hex()
        )
        assert (
            response.json()["result"]["secondaryColor"]
            == Color(update_data["secondary_color"]).as_hex()
        )
        assert (
            response.json()["result"]["tertiaryColor"]
            == Color(update_data["tertiary_color"]).as_hex()
        )

    @transaction.rollback
    async def test_themes_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(self.list_url)

        assert response.status_code == 200
        assert type(response.json()["result"]) == list
