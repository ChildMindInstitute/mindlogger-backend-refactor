from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestNotificationLogs(BaseTest):
    create_log_url = "/logs/notification"
    query_log_url = "/logs/notification?"

    @transaction.rollback
    async def test_create_log(self):
        create_data = dict(
            user_id="test@test.com",
            device_id="test_device_id",
            action_type="test",
            notification_descriptions='{"sample":"json"}',
            notification_in_queue='{"sample":"json"}',
            scheduled_notifications='{"sample":"json"}',
        )

        response = await self.client.post(
            self.create_log_url, data=create_data
        )
        assert response.status_code == 201, response.json()
        assert response.json()["Result"]["Id"] == 1

    @transaction.rollback
    async def test_retrieve_log(self):
        query = dict(user_id="test@test.com", device_id="test_device_id")

        response = await self.client.get(self.query_log_url, query=query)

        assert response.status_code == 200, response.json()
        assert type(response.json()["Results"]) == list

        create_data = dict(
            user_id="test@test.com",
            device_id="test_device_id",
            action_type="test",
            notification_descriptions='{"sample":"json"}',
            notification_in_queue='{"sample":"json"}',
            scheduled_notifications='{"sample":"json"}',
        )

        response = await self.client.post(
            self.create_log_url, data=create_data
        )
        assert response.status_code == 201, response.json()
        assert response.json()["Result"]["Id"] == 1

        query = dict(
            user_id="test@test.com", device_id="test_device_id", limit=10
        )

        response = await self.client.get(self.query_log_url, query=query)

        assert response.status_code == 200, response.json()
        assert len(response.json()["Results"]) == 1
