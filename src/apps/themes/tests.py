from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestThemes(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/token"
    create_url = "themes/"
    update_url = "themes/{id}"
    delete_url = "themes/{id}"

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

        response = await self.client.post(self.create_url, data=create_data)

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

        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"] == 1

        response = await self.client.delete(self.delete_url.format(id=1))

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

        response = await self.client.post(self.create_url, data=create_data)

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
            self.delete_url.format(id=1), data=update_data
        )

        assert response.status_code == 204, response.json()
