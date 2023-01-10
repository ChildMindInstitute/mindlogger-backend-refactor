from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestReusableItem(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/token"
    create_url = "activity/item_choices"
    update_url = "activity/item_choices"
    delete_url = "activity/item_choices/{id}"

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
        assert response.json()["Result"]["Id"] == 1

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
        assert response.json()["Result"]["Id"] == 1

        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        res_data = response.json()
        assert response.status_code == 400, res_data
        assert res_data["messages"][0] == "Reusable item choice already exist"

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
        assert response.json()["Result"]["Id"] == 1

        response = await self.client.delete(self.delete_url.format(id=1))

        assert response.status_code == 204, response.json()
