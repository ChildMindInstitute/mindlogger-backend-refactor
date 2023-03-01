from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestReusableItem(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/login"
    create_url = "activities/item_choices"
    update_url = "activities/item_choices"
    delete_url = "activities/item_choices/{id}"

    @transaction.rollback
    async def test_create_item_choice(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

    @transaction.rollback
    async def test_recreate_item_choice(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        res_data = response.json()
        assert response.status_code == 400, res_data
        assert (
            res_data["result"][0]["message"]["en"]
            == "Reusable item choice already exist"
        )

    @transaction.rollback
    async def test_delete_item_choice(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        response = await self.client.delete(
            self.delete_url.format(id=response.json()["result"]["id"])
        )

        assert response.status_code == 204, response.json()
