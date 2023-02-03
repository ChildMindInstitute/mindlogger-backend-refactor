from apps.answers.router import router as answer_activity_router
from apps.authentication.router import router as auth_router
from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "applets/fixtures/applet_histories.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_histories.json",
        "activities/fixtures/activity_items.json",
        "activities/fixtures/activity_item_histories.json",
        "activity_flows/fixtures/activity_flows.json",
    ]

    login_url = auth_router.url_path_for("get_token")
    answer_activity_item_create_url = answer_activity_router.url_path_for(
        "answer_activity_item_create"
    )

    @transaction.rollback
    async def test_answer_activity_items_create_for_respondent(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = dict(
            appletId=1,
            appletHistoryVersion="1.0.0",
            activityId=1,
            answers=[
                dict(
                    activityItemHistoryId=1,
                    answer=dict(
                        additionalProp1="string",
                        additionalProp2="string",
                        additionalProp3="string",
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
            appletId=1,
            appletHistoryVersion="1.0.0",
            activityId=1,
            answers=[
                dict(
                    activityItemHistoryId=1,
                    answer=dict(
                        additionalProp1="string",
                        additionalProp2="string",
                        additionalProp3="string",
                    ),
                )
            ],
        )

        response = await self.client.post(
            self.answer_activity_item_create_url, data=create_data
        )

        assert response.status_code == 400, response.json()
