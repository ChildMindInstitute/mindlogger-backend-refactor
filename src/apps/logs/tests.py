import json

from pytest import fixture, mark

from apps.shared.test import BaseTest
from infrastructure.database import rollback


@fixture(scope="function")
def dummy_logs_payload() -> list[dict]:
    return [
        dict(
            user_id="test@test.com",
            device_id="test@test.com__device_id",
            action_type=f"test{i}",
            notification_descriptions=json.dumps(
                [{"sample": f"descriptions{i}"}]
            ),
            notification_in_queue=json.dumps([{"sample": f"queue{i}"}]),
            scheduled_notifications=json.dumps([{"sample": f"scheduled{i}"}]),
        )
        for i in range(2)
    ]


class TestNotificationLogs(BaseTest):
    logs_url = "/logs/notification"

    @rollback
    async def test_create_log(self):
        create_data = dict(
            user_id="test@test.com",
            device_id="test_device_id",
            action_type="test",
            notification_descriptions='[{"sample":"json"}]',
            notification_in_queue='[{"sample":"json"}]',
            scheduled_notifications='[{"sample":"json"}]',
        )

        response = await self.client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

    @rollback
    async def test_retrieve_log(self, dummy_logs_payload):
        query = dict(user_id="test@test.com", device_id="test_device_id")

        response = await self.client.get(self.logs_url, query=query)

        assert response.status_code == 200, response.json()
        assert type(response.json()["result"]) == list

        create_data = dict(
            user_id="test@test.com",
            device_id="test_device_id",
            action_type="test",
            notification_descriptions='[{"sample":"json"}]',
            notification_in_queue='[{"sample":"json"}]',
            scheduled_notifications='[{"sample":"json"}]',
        )

        response = await self.client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        query = dict(
            user_id="test@test.com", device_id="test_device_id", limit=10
        )

        response = await self.client.get(self.logs_url, query=query)

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 1

    @mark.parametrize(
        "description,queue,scheduled",
        (
            ('[{"sample":"json"}]', json.dumps(None), json.dumps(None)),
            (json.dumps(None), '[{"sample":"json"}]', json.dumps(None)),
            (json.dumps(None), json.dumps(None), '[{"sample":"json"}]'),
            (
                '[{"sample":"json0"}]',
                '[{"sample":"json1"}]',
                '[{"sample":"json2"}]',
            ),
        ),
    )
    @rollback
    async def test_create_log_use_previous_value_if_attribute_null(
        self, dummy_logs_payload, description, queue, scheduled
    ):
        for payload in dummy_logs_payload:
            response = await self.client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        create_data = dict(
            user_id="test@test.com",
            device_id="test@test.com__device_id",
            action_type="test",
            notification_descriptions=description,
            notification_in_queue=queue,
            scheduled_notifications=scheduled,
        )

        response = await self.client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"]
        assert response["notificationInQueue"]
        assert response["scheduledNotifications"]

    @rollback
    async def test_create_log_use_none_value_if_attribute_null_at_first_log(
        self,
    ):
        response = await self.client.post(
            self.logs_url,
            data=dict(
                user_id="test@test.com",
                device_id="test@test.com__device_id",
                action_type="test",
                notification_descriptions=None,
                notification_in_queue='[{"name":"notification_in_queue"}]',
                scheduled_notifications='[{"name":"scheduled_notifications"}]',
            ),
        )
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"] is None
        assert response["notificationInQueue"]
        assert response["scheduledNotifications"]

    @rollback
    async def test_create_log_use_previous_non_null_if_attribute_null(self):
        payloads = [
            dict(
                user_id="test@test.com",
                device_id="test@test.com__device_id",
                action_type="test",
                notification_descriptions='[{"name":"descriptions1"}]',
                notification_in_queue='[{"name":"in_queue1"}]',
                scheduled_notifications='[{"name":"notifications1"}]',
            ),
            dict(
                user_id="test@test.com",
                device_id="test@test.com__device_id",
                action_type="test",
                notification_descriptions=None,
                notification_in_queue='[{"name":"in_queue2"}]',
                scheduled_notifications='[{"name":"notifications2"}]',
            ),
        ]
        for payload in payloads:
            response = await self.client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        create_data = dict(
            user_id="test@test.com",
            device_id="test@test.com__device_id",
            action_type="test",
            notification_descriptions=None,
            notification_in_queue='[{"name":"in_queue3"}]',
            scheduled_notifications='[{"name":"notifications3"}]',
        )

        response = await self.client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"] == json.loads(
            '[{"name":"descriptions1"}]'
        )
        assert response["notificationInQueue"] == json.loads(
            '[{"name":"in_queue3"}]'
        )
        assert response["scheduledNotifications"] == json.loads(
            '[{"name":"notifications3"}]'
        )
