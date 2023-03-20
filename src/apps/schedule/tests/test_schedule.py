from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestSchedule(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
        "schedule/fixtures/periodicity.json",
        "schedule/fixtures/events.json",
        "schedule/fixtures/activity_events.json",
        "schedule/fixtures/flow_events.json",
        "schedule/fixtures/user_events.json",
    ]

    login_url = "/auth/login"
    applet_detail_url = "applets/{applet_id}"

    schedule_user_url = "users/me/events"
    schedule_detail_user_url = f"{schedule_user_url}/{{applet_id}}"

    schedule_url = f"{applet_detail_url}/events"
    delete_user_url = f"{schedule_url}/delete_individual/{{respondent_id}}"
    schedule_detail_url = f"{applet_detail_url}/events/{{event_id}}"

    count_url = "applets/{applet_id}/events/count"

    @transaction.rollback
    async def test_schedule_create_with_activity(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": False,
            "one_time_completion": False,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "ONCE",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": None,
            "activity_id": "09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            "flow_id": None,
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["startTime"] == create_data["start_time"]

    @transaction.rollback
    async def test_schedule_create_with_respondent_id(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "WEEKLY",
                "start_date": "2021-09-01",
                "end_date": "2023-09-01",
                "selected_date": "2023-01-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "activity_id": "09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
            "flow_id": None,
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    @transaction.rollback
    async def test_schedule_create_with_flow(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]
        assert event["flowId"] == create_data["flow_id"]

    @transaction.rollback
    async def test_schedule_get_all(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert type(events) == list
        events_count = len(events)

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5832",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        response = await self.client.get(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert len(events) == events_count + 1

    @transaction.rollback
    async def test_schedule_get_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )

        assert response.status_code == 200, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    @transaction.rollback
    async def test_schedule_delete_all(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 204

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.delete(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 204

    @transaction.rollback
    async def test_schedule_delete_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event = response.json()["result"]

        response = await self.client.delete(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event["id"],
            )
        )

        assert response.status_code == 204

    @transaction.rollback
    async def test_schedule_update(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event = response.json()["result"]

        create_data["activity_id"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        create_data["flow_id"] = None
        create_data["respondent_id"] = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"

        response = await self.client.put(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event["id"],
            ),
            data=create_data,
        )
        assert response.status_code == 200

        event = response.json()["result"]

        assert event["flowId"] == create_data["flow_id"]
        assert event["respondentId"] == create_data["respondent_id"]
        assert event["activityId"] == create_data["activity_id"]

    @transaction.rollback
    async def test_count(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.count_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        create_data["activity_id"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        create_data["flow_id"] = None
        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        response = await self.client.get(
            self.count_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
        )

        assert response.status_code == 200

        result = response.json()["result"]

        assert type(result["activityEvents"][0]["count"]) == int
        assert type(result["flowEvents"][0]["count"]) == int

    @transaction.rollback
    async def test_schedule_delete_user(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.delete(
            self.delete_user_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            )
        )

        assert response.status_code == 404  # event for user not found

        create_data = {
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "access_before_schedule": True,
            "one_time_completion": True,
            "timer": "00:00:00",
            "timer_type": "NOT_SET",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
            "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await self.client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )

        assert response.status_code == 200
        assert (
            response.json()["result"]["respondentId"]
            == create_data["respondent_id"]
        )

        response = await self.client.delete(
            self.delete_user_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            )
        )

        assert response.status_code == 204

        response = await self.client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )
        assert response.status_code == 404

    @transaction.rollback
    async def test_schedules_get_user_all(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(self.schedule_user_url)
        assert response.status_code == 200

    @transaction.rollback
    async def test_schedule_get_user_by_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.get(
            self.schedule_detail_user_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200
