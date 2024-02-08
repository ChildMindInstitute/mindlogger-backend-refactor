from pydantic.color import Color

from apps.shared.test import BaseTest


class TestThemes(BaseTest):
    login_url = "/auth/login"
    list_url = "/themes"
    detail_url = "themes/{id}"

    async def test_create_theme(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await client.post(self.list_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

    async def test_delete_theme(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await client.post(self.list_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        response = await client.delete(self.detail_url.format(id=response.json()["result"]["id"]))

        assert response.status_code == 204, response.json()

    async def test_update_theme(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            name="Test theme",
            logo="test/logo.png",
            background_image="test/background.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )

        response = await client.post(self.list_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        update_data = dict(
            name="Test theme 2",
            logo="test/logo2.png",
            background_image="test/background2.png",
            primary_color="#000000",
            secondary_color="#000000",
            tertiary_color="#000000",
        )
        response = await client.put(
            self.detail_url.format(id=response.json()["result"]["id"]),
            data=update_data,
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["id"]
        assert response.json()["result"]["name"] == update_data["name"]
        assert response.json()["result"]["logo"] == update_data["logo"]
        assert response.json()["result"]["backgroundImage"] == update_data["background_image"]
        assert response.json()["result"]["primaryColor"] == Color(update_data["primary_color"]).as_hex()
        assert response.json()["result"]["secondaryColor"] == Color(update_data["secondary_color"]).as_hex()
        assert response.json()["result"]["tertiaryColor"] == Color(update_data["tertiary_color"]).as_hex()

    async def test_themes_list(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(self.list_url)

        assert response.status_code == 200
        assert isinstance(response.json()["result"], list)
