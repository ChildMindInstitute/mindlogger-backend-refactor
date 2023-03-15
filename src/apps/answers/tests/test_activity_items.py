from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestAnswerActivityItems(BaseTest):
    # TODO: fix text
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "applets/fixtures/applet_histories.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_histories.json",
        "activities/fixtures/activity_items.json",
        "activities/fixtures/activity_item_histories.json",
        "activity_flows/fixtures/activity_flows.json",
    ]

    login_url = "/auth/login"
    answer_activity_item_create_url = "/answers/"

    @transaction.rollback
    async def test_answer_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            applet_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            answers=[
                dict(
                    activity_item_id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    answer=dict(
                        value="string",
                    ),
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @transaction.rollback
    async def test_answer_activity_items_create_for_not_respondent(self):
        await self.client.login(self.login_url, "bob@gmail.com", "Test1234!")

        create_data = dict(
            applet_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            version="1.0.0",
            activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            answers=[
                dict(
                    activity_item_id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                    answer=dict(
                        value="string",
                    ),
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 400, response.json()
