from apps.shared.test import BaseTest


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
        "schedule/fixtures/notifications.json",
        "schedule/fixtures/reminders.json",
    ]

    login_url = "/auth/login"
    applet_detail_url = "applets/{applet_id}"

    schedule_user_url = "users/me/events"
    schedule_detail_user_url = f"{schedule_user_url}/{{applet_id}}"

    erspondent_schedules_user_two_weeks_url = (
        "/users/me/respondent/current_events"
    )

    schedule_url = f"{applet_detail_url}/events"
    schedule_import_url = f"{applet_detail_url}/events/import"
    schedule_create_individual = (
        f"{applet_detail_url}/events/individual/{{respondent_id}}"
    )

    delete_user_url = (
        f"{applet_detail_url}/events/delete_individual/{{respondent_id}}"
    )
    remove_ind_url = (
        f"{applet_detail_url}/events/remove_individual/{{respondent_id}}"
    )

    schedule_detail_url = f"{applet_detail_url}/events/{{event_id}}"

    count_url = "applets/{applet_id}/events/count"

    public_events_url = "public/applets/{key}/events"

    async def test_schedule_create_with_equal_start_end_time(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = {
            "start_time": "08:00:00",
            "end_time": "08:00:00",
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
            "notification": {
                "notifications": [
                    {"trigger_type": "FIXED", "at_time": "08:30:00"},
                ],
                "reminder": {
                    "activity_incomplete": 1,
                    "reminder_time": "08:30:00",
                },
            },
        }

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        assert response.status_code == 422

    async def test_schedule_create_with_activity(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
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
            "notification": {
                "notifications": [
                    {"trigger_type": "FIXED", "at_time": "08:30:00"},
                ],
                "reminder": {
                    "activity_incomplete": 1,
                    "reminder_time": "08:30:00",
                },
            },
        }

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["startTime"] == create_data["start_time"]

    async def test_schedule_create_with_respondent_id(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    async def test_schedule_create_with_flow(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]
        assert event["flowId"] == create_data["flow_id"]

    async def test_schedule_get_all(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert isinstance(events, list)
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        response = await client.get(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert len(events) == events_count

        response = await client.get(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
            + "?respondentId=7484f34a-3acc-4ee6-8a94-fd7299502fa2"
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert len(events) == 1

    async def test_public_schedule_get_all(self, client):
        response = await client.get(
            self.public_events_url.format(
                key="51857e10-6c05-4fa8-a2c8-725b8c1a0aa6"
            )
        )

        assert response.status_code == 200, response.json()
        events = response.json()["result"]
        assert isinstance(events, dict)

    async def test_schedule_get_detail(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )

        assert response.status_code == 200, response.json()
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    async def test_schedule_delete_all(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.delete(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 204

    async def test_schedule_delete_detail(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event = response.json()["result"]

        response = await client.delete(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event["id"],
            )
        )

        assert response.status_code == 204

    async def test_schedule_update_with_equal_start_end_time(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
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
            "notification": {
                "notifications": [
                    {"trigger_type": "FIXED", "at_time": "08:30:00"},
                ],
                "reminder": {
                    "activity_incomplete": 1,
                    "reminder_time": "08:30:00",
                },
            },
        }

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event = response.json()["result"]

        update_data = {
            "start_time": "00:00:15",
            "end_time": "00:00:15",
            "periodicity": {
                "type": "MONTHLY",
                "start_date": "2021-09-01",
                "end_date": "2021-09-01",
                "selected_date": "2023-09-01",
            },
        }

        response = await client.put(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event["id"],
            ),
            data=update_data,
        )
        assert response.status_code == 422

    async def test_schedule_update(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
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
            "notification": {
                "notifications": [
                    {"trigger_type": "FIXED", "at_time": "08:30:00"},
                ],
                "reminder": {
                    "activity_incomplete": 1,
                    "reminder_time": "08:30:00",
                },
            },
        }

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event = response.json()["result"]
        create_data.pop("activity_id")
        create_data.pop("flow_id")
        create_data.pop("respondent_id")

        create_data["notification"]["notifications"] = [
            {
                "trigger_type": "RANDOM",
                "from_time": "08:30:00",
                "to_time": "08:40:00",
            },
        ]
        create_data["notification"]["reminder"] = {
            "activity_incomplete": 2,
            "reminder_time": "08:40:00",
        }

        response = await client.put(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event["id"],
            ),
            data=create_data,
        )
        assert response.status_code == 200

        event = response.json()["result"]

        assert (
            event["notification"]["reminder"]["reminderTime"]
            == create_data["notification"]["reminder"]["reminder_time"]
        )

    async def test_count(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
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
            # "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            "activity_id": None,
            "flow_id": "3013dfb1-9202-4577-80f2-ba7450fb5831",
        }

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        create_data["activity_id"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        create_data["flow_id"] = None
        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201

        response = await client.get(
            self.count_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
        )

        assert response.status_code == 200

        result = response.json()["result"]

        assert isinstance(result["activityEvents"], list)
        assert isinstance(result["flowEvents"], list)

    async def test_schedule_delete_user(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(
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
            "timer": None,
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
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

        response = await client.delete(
            self.delete_user_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )
        assert response.status_code == 404

    async def test_schedules_get_user_all(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(self.schedule_user_url)

        assert response.status_code == 200
        assert response.json()["count"] == 6

    async def test_respondent_schedules_get_user_two_weeks(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.erspondent_schedules_user_two_weeks_url
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2

        data = sorted(response.json()["result"], key=lambda x: x["appletId"])
        apppet_0 = data[0]
        apppet_1 = data[1]
        assert set(apppet_0.keys()) == {
            "appletId",
            "events",
        }

        apppet_0["appletId"] = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        assert len(apppet_0["events"]) == 3
        events_data = sorted(apppet_0["events"], key=lambda x: x["id"])
        assert set(events_data[0].keys()) == {
            "id",
            "entityId",
            "availability",
            "selectedDate",
            "timers",
            "availabilityType",
            "notificationSettings",
        }
        assert set(events_data[0]["availability"].keys()) == {
            "oneTimeCompletion",
            "periodicityType",
            "timeFrom",
            "timeTo",
            "allowAccessBeforeFromTime",
            "startDate",
            "endDate",
        }
        events_data[0]["id"] = "04c93c4a-2cd4-45ce-9aec-b1912f330584"
        events_data[0]["entityId"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3612"
        events_data[1]["id"] = "04c93c4a-2cd4-45ce-9aec-b1912f330583"
        events_data[1]["entityId"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        events_data[2]["id"] = "04c93c4a-2cd4-45ce-9aec-b1912f330582"
        events_data[2]["entityId"] = "3013dfb1-9202-4577-80f2-ba7450fb5832"

        apppet_1["appletId"] = "92917a56-d586-4613-b7aa-991f2c4b15b2"
        assert len(apppet_1["events"]) == 1
        # events_data = sorted(apppet_1["events"], key=lambda x: x["id"])
        events_data = apppet_1["events"]
        assert set(events_data[0].keys()) == {
            "id",
            "entityId",
            "availability",
            "selectedDate",
            "timers",
            "availabilityType",
            "notificationSettings",
        }
        assert set(events_data[0]["availability"].keys()) == {
            "oneTimeCompletion",
            "periodicityType",
            "timeFrom",
            "timeTo",
            "allowAccessBeforeFromTime",
            "startDate",
            "endDate",
        }
        events_data[0]["id"] = "04c93c4a-2cd4-45ce-9aec-b1912f330584"
        events_data[0]["entityId"] = "09e3dbf0-aefb-4d0e-9177-bdb321bf3612"

    async def test_schedule_get_user_by_applet(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(
            self.schedule_detail_user_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200

    async def test_schedule_remove_individual(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.delete(
            self.remove_ind_url.format(
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
            "timer": None,
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

        response = await client.post(
            self.schedule_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
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

        response = await client.delete(
            self.remove_ind_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
            )
        )

        assert response.status_code == 204

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                event_id=event_id,
            )
        )
        assert response.status_code == 404

    async def test_schedule_import(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        create_data = [
            {
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
            },
            {
                "start_time": "08:00:00",
                "end_time": "09:00:00",
                "access_before_schedule": True,
                "one_time_completion": True,
                "timer": "00:00:00",
                "timer_type": "NOT_SET",
                "periodicity": {
                    "type": "DAILY",
                    "start_date": "2021-09-01",
                    "end_date": "2023-09-01",
                    "selected_date": "2023-01-01",
                },
                "respondent_id": "7484f34a-3acc-4ee6-8a94-fd7299502fa2",
                "activity_id": "09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                "flow_id": None,
            },
        ]

        response = await client.post(
            self.schedule_import_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=create_data,
        )

        assert response.status_code == 201, response.json()
        events = response.json()["result"]
        assert len(events) == 2
        assert events[0]["respondentId"] == create_data[0]["respondent_id"]

    async def test_schedule_create_individual(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.schedule_create_individual.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                respondent_id="7484f34a-3acc-4ee6-8a94-fd7299502fa2",
            ),
        )
        assert response.status_code == 201

        events = response.json()["result"]
        assert len(events) == 3
        assert (
            events[0]["respondentId"] == "7484f34a-3acc-4ee6-8a94-fd7299502fa2"
        )
