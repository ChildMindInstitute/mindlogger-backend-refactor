from pytest import fixture, mark

from apps.shared.test import BaseTest

EMPTY_DESCRIPTIONS = [
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test1",
        notification_descriptions=None,
        notification_in_queue=[{"name": "in_queue1"}],
        scheduled_notifications=[{"name": "notifications1"}],
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test2",
        notification_descriptions=[],
        notification_in_queue=[{"name": "in_queue2"}],
        scheduled_notifications=[{"name": "notifications2"}],
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test3",
        notification_descriptions=None,
        notification_in_queue=[{"name": "in_queue2"}],
        scheduled_notifications=[{"name": "notifications2"}],
    ),
]

EMPTY_QUEUE = [
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test1",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=None,
        scheduled_notifications=[{"name": "notifications1"}],
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test2",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=[],
        scheduled_notifications=[{"name": "notifications2"}],
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test3",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=None,
        scheduled_notifications=[{"name": "notifications2"}],
    ),
]

EMPTY_SCHEDULE = [
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test1",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=[{"name": "in_queue1"}],
        scheduled_notifications=None,
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test2",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=[{"name": "in_queue2"}],
        scheduled_notifications=[],
    ),
    dict(
        user_id="tom@mindlogger.com",
        device_id="deviceid",
        action_type="test3",
        notification_descriptions=[{"name": "description"}],
        notification_in_queue=[{"name": "in_queue2"}],
        scheduled_notifications=None,
    ),
]


@fixture(scope="function")
def dummy_logs_payload() -> list[dict]:
    return [
        dict(
            user_id="tom@mindlogger.com",
            device_id="deviceid",
            action_type=f"test{i}",
            notification_descriptions=[{"sample": f"descriptions{i}"}],
            notification_in_queue=[{"sample": f"queue{i}"}],
            scheduled_notifications=[{"sample": f"scheduled{i}"}],
        )
        for i in range(2)
    ]


class TestNotificationLogs(BaseTest):
    logs_url = "/logs/notification"

    async def test_create_log(self, client, device_tom):
        create_data = dict(
            user_id="tom@mindlogger.com",
            device_id="deviceid",
            action_type="test",
            notification_descriptions=[{"sample": "json"}],
            notification_in_queue=[{"sample": "json"}],
            scheduled_notifications=[{"sample": "json"}],
        )

        response = await client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

    async def test_retrieve_log(self, client, device_tom):
        query = dict(
            email="tom@mindlogger.com",
            device_id=device_tom,
        )

        response = await client.get(self.logs_url, query=query)

        assert response.status_code == 200, response.json()
        assert isinstance(response.json()["result"], list)

        new_device_id = "new_device_id"
        create_data = dict(
            user_id="tom@mindlogger.com",
            device_id=new_device_id,
            action_type="test",
            notification_descriptions=[{"sample": "json"}],
            notification_in_queue=[{"sample": "json"}],
            scheduled_notifications=[{"sample": "json"}],
        )

        response = await client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        assert response.json()["result"]["id"]

        query = dict(
            email="tom@mindlogger.com",
            device_id=new_device_id,
            limit=10,
        )

        response = await client.get(self.logs_url, query=query)

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 1

    @mark.parametrize(
        "description,queue,scheduled",
        (
            ([{"sample": "json"}], None, None),
            (None, [{"sample": "json"}], None),
            (None, None, [{"sample": "json"}]),
            (
                [{"sample": "json0"}],
                [{"sample": "json1"}],
                [{"sample": "json2"}],
            ),
        ),
    )
    async def test_create_log_use_previous_value_if_attribute_null(
        self, client, dummy_logs_payload, description, queue, scheduled
    ):
        for payload in dummy_logs_payload:
            response = await client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        create_data = dict(
            user_id="tom@mindlogger.com",
            device_id="deviceid",
            action_type="test",
            notification_descriptions=description,
            notification_in_queue=queue,
            scheduled_notifications=scheduled,
        )

        response = await client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"]
        assert response["notificationInQueue"]
        assert response["scheduledNotifications"]

    async def test_create_log_use_none_value_if_attribute_null_at_first_log(self, client):
        response = await client.post(
            self.logs_url,
            data=dict(
                user_id="tom@mindlogger.com",
                device_id="deviceid",
                action_type="test",
                notification_descriptions=None,
                notification_in_queue=[{"name": "notification_in_queue"}],
                scheduled_notifications=[{"name": "scheduled_notifications"}],
            ),
        )
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"] is None
        assert response["notificationInQueue"]
        assert response["scheduledNotifications"]

    async def test_create_log_use_previous_non_null_if_attribute_null(self, client):
        payloads = [
            dict(
                user_id="tom@mindlogger.com",
                device_id="deviceid",
                action_type="test",
                notification_descriptions=[{"name": "descriptions1"}],
                notification_in_queue=[{"name": "in_queue1"}],
                scheduled_notifications=[{"name": "notifications1"}],
            ),
            dict(
                user_id="tom@mindlogger.com",
                device_id="deviceid",
                action_type="test",
                notification_descriptions=None,
                notification_in_queue=[{"name": "in_queue2"}],
                scheduled_notifications=[{"name": "notifications2"}],
            ),
        ]
        for payload in payloads:
            response = await client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        create_data = dict(
            user_id="tom@mindlogger.com",
            device_id="deviceid",
            action_type="test",
            notification_descriptions=None,
            notification_in_queue=[{"name": "in_queue3"}],
            scheduled_notifications=[{"name": "notifications3"}],
        )

        response = await client.post(self.logs_url, data=create_data)
        assert response.status_code == 201, response.json()
        response = response.json()["result"]
        assert response["id"]
        assert response["notificationDescriptions"] == [{"name": "descriptions1"}]
        assert response["notificationInQueue"] == [{"name": "in_queue3"}]
        assert response["scheduledNotifications"] == [{"name": "notifications3"}]

    async def test_create_log_allow_empty_array(self, client):
        payloads = [
            dict(
                user_id="tom@mindlogger.com",
                device_id="deviceid",
                action_type="test",
                notification_descriptions=[{"name": "descriptions1"}],
                notification_in_queue=[{"name": "in_queue1"}],
                scheduled_notifications=[{"name": "notifications1"}],
            ),
            dict(
                user_id="tom@mindlogger.com",
                device_id="deviceid",
                action_type="test",
                notification_descriptions=[],
                notification_in_queue=[{"name": "in_queue2"}],
                scheduled_notifications=[{"name": "notifications2"}],
            ),
        ]

        for payload in payloads:
            response = await client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        query = dict(
            email="tom@mindlogger.com",
            device_id="deviceid",
            limit=5,
        )

        response = await client.get(self.logs_url, query=query)
        assert response.status_code == 200, response.json()
        response = response.json()["result"]
        has_empty_array = next(
            filter(lambda x: x["notificationDescriptions"] == [], response),
            None,
        )
        assert has_empty_array

    @mark.parametrize(
        "param,payloads",
        (
            ("notificationDescriptions", EMPTY_DESCRIPTIONS),
            ("notificationInQueue", EMPTY_QUEUE),
            (
                "scheduledNotifications",
                EMPTY_SCHEDULE,
            ),
        ),
    )
    async def test_create_log_allow_empty_array_if_prev_is_none(self, client, param, payloads):
        for payload in payloads:
            response = await client.post(self.logs_url, data=payload)
            assert response.status_code == 201

        query = dict(
            email="tom@mindlogger.com",
            device_id="deviceid",
            limit=5,
        )

        response = await client.get(self.logs_url, query=query)
        assert response.status_code == 200, response.json()
        response = response.json()["result"]
        log_1 = next(filter(lambda x: x["actionType"] == "test1", response))
        log_2 = next(filter(lambda x: x["actionType"] == "test2", response))
        log_3 = next(filter(lambda x: x["actionType"] == "test3", response))
        assert log_1[param] is None
        assert log_2[param] == []
        assert log_3[param] == []
