from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestSchedule(BaseTest):

    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
    ]

    login_url = "/auth/login"
    applet_detail_url = "applets/{applet_id}"

    schedule_url = applet_detail_url + "/events"
    schedule_detail_url = applet_detail_url + "/events/{event_id}"

    @transaction.rollback
    async def test_schedule_create_with_activity(self):

        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": False,
            "one_time_completion": False,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "ONCE",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 0,
            },
            "user_ids": [],
            "activity_id": 1,
            "flow_id": None,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["startTime"] == create_data["start_time"]

    @transaction.rollback
    async def test_schedule_create_with_user_ids(self):

        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "WEEKLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 4,
            },
            "user_ids": [],
            "activity_id": 1,
            "flow_id": None,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["userIds"] == create_data["user_ids"]

    @transaction.rollback
    async def test_schedule_create_with_flow(self):

        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 1,
            },
            "user_ids": [1, 2],
            "activity_id": None,
            "flow_id": 1,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["userIds"] == create_data["user_ids"]
        assert event["flowId"] == create_data["flow_id"]

    @transaction.rollback
    async def test_schedule_get_all(self):

        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.schedule_url.format(applet_id=1))

        assert response.status_code == 200, response.json()
        events = response.json()["results"]
        assert len(events) == 0

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 1,
            },
            "user_ids": [1, 2],
            "activity_id": None,
            "flow_id": 1,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        response = await self.client.get(self.schedule_url.format(applet_id=1))

        assert response.status_code == 200, response.json()
        events = response.json()["results"]
        assert len(events) == 1

    @transaction.rollback
    async def test_schedule_get_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.schedule_detail_url.format(applet_id=1, event_id=1)
        )

        assert response.status_code == 404, response.json()

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 1,
            },
            "user_ids": [1, 2],
            "activity_id": None,
            "flow_id": 1,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        response = await self.client.get(
            self.schedule_detail_url.format(applet_id=1, event_id=1)
        )

        assert response.status_code == 200, response.json()
        event = response.json()["result"]
        assert event["id"] == 1

    @transaction.rollback
    async def test_schedule_delete_all(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.schedule_url.format(applet_id=1)
        )

        assert response.status_code == 404

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 1,
            },
            "user_ids": [1, 2],
            "activity_id": None,
            "flow_id": 1,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )

        response = await self.client.delete(
            self.schedule_url.format(applet_id=1)
        )

        assert response.status_code == 204

    @transaction.rollback
    async def test_schedule_delete_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.schedule_detail_url.format(applet_id=1, event_id=1)
        )

        assert response.status_code == 404

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "all_day": False,
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "interval": 1,
            },
            "user_ids": [1, 2],
            "activity_id": None,
            "flow_id": 1,
        }

        response = await self.client.post(
            self.schedule_url.format(applet_id=1), data=create_data
        )
        event = response.json()["result"]

        response = await self.client.delete(
            self.schedule_detail_url.format(applet_id=1, event_id=event["id"])
        )

        assert response.status_code == 204
