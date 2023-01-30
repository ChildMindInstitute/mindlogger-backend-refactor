from starlette import status

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
    async def test_schedule_create(self):

        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = {
            "start_time": "2021-09-01T00:00:00",
            "end_time": "2021-09-01T00:00:00",
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

        assert response.status_code == 200, response.json()
        event = response.json()["result"]
        assert event["start_time"] == create_data["start_time"]
