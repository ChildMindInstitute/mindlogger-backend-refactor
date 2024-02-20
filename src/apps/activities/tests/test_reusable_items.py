import uuid


class TestReusableItem:
    login_url = "/auth/login"
    create_url = "activities/item_choices"
    update_url = "activities/item_choices"
    delete_url = "activities/item_choices/{id}"
    retrieve_url = "activities/item_choices"

    async def test_create_item_choice(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            token_name="Average age",
            token_value="21",
            input_type="radiobutton",
        )

        response = await client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

    async def test_recreate_item_choice(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            token_name="Average age 2",
            token_value="21",
            input_type="radiobutton",
        )

        response = await client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        create_data = dict(
            token_name="Average age 2",
            token_value="21",
            input_type="radiobutton",
        )

        response = await client.post(
            self.create_url,
            data=create_data,
        )

        res_data = response.json()
        assert response.status_code == 400, res_data
        assert res_data["result"][0]["message"] == "Reusable item choice already exist."

    async def test_delete_item_choice(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            token_name="Average age 3",
            token_value="21",
            input_type="radiobutton",
        )

        response = await client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        response = await client.delete(self.delete_url.format(id=response.json()["result"]["id"]))

        assert response.status_code == 204, response.json()

    async def test_delete_item_choice_does_not_exist(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(self.delete_url.format(id=str(uuid.uuid4())))

        assert response.status_code == 404, response.json()

    async def test_create_item_choice_with_long_int_value(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            token_name="Average age",
            token_value=12321312312312323,
            input_type="radiobutton",
        )

        response = await client.post(self.create_url, data=create_data)

        res_data = response.json()
        assert response.status_code == 422, res_data

    async def test_retrieve_item_choice(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = dict(
            token_name="Average age 3",
            token_value="21",
            input_type="radiobutton",
        )

        response = await client.post(self.create_url, data=create_data)
        created_data = response.json()["result"]
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        response = await client.get(self.retrieve_url)
        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0] == created_data
