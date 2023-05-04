import uuid

import pytest

from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestReusableItem(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/login"
    create_url = "activities/item_choices"
    update_url = "activities/item_choices"
    delete_url = "activities/item_choices/{id}"

    @rollback
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

    @rollback
    async def test_recreate_item_choice(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age 2",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        create_data = dict(
            token_name="Average age 2",
            token_value="21",
            input_type="radiobutton",
        )

        response = await self.client.post(
            self.create_url,
            data=create_data,
        )

        res_data = response.json()
        assert response.status_code == 400, res_data
        assert (
            res_data["result"][0]["message"]
            == "Reusable item choice already exist."
        )

    @rollback
    async def test_delete_item_choice(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age 3",
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

    @rollback
    async def test_delete_item_choice_does_not_exist(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.delete_url.format(id=str(uuid.uuid4()))
        )

        assert response.status_code == 404, response.json()

    @rollback
    async def test_create_item_choice_with_long_int_value(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            token_name="Average age",
            token_value=12321312312312323,
            input_type="radiobutton",
        )

        response = await self.client.post(self.create_url, data=create_data)

        res_data = response.json()
        assert response.status_code == 422, res_data
