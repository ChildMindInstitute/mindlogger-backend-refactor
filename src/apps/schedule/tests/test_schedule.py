from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.applets.tests.utils import teardown_applet
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.themes.service import ThemeService
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture(scope="class")
async def applet_data(applet_minimal_data: AppletCreate) -> AppletCreate:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "schedule"
    data.activity_flows = [
        FlowCreate(
            name="flow",
            description={Language.ENGLISH: "description"},
            items=[FlowItemCreate(activity_key=data.activities[0].key)],
        )
    ]
    return AppletCreate(**data.dict())


@pytest.fixture(scope="class")
async def applet(
    global_session: AsyncSession, user: User, applet_data: AppletCreate
) -> AsyncGenerator[AppletFull, None]:
    srv = AppletService(global_session, user.id)
    await ThemeService(global_session, user.id).get_or_create_default()
    applet = await srv.create(applet_data)
    await global_session.commit()
    yield applet
    await teardown_applet(global_session, applet.id)


@pytest.fixture(scope="class")
async def applet_lucy_respondent(
    global_session: AsyncSession, applet: AppletFull, user: User, lucy: User
) -> AsyncGenerator[AppletFull, None]:
    await UserAppletAccessService(global_session, user.id, applet.id).add_role(lucy.id, Role.RESPONDENT)
    await global_session.commit()
    yield applet
    await UserAppletAccessCRUD(global_session)._delete(applet_id=applet.id)
    await global_session.commit()


@pytest.mark.usefixtures("applet", "applet_lucy_respondent")
class TestSchedule(BaseTest):
    fixtures = [
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

    erspondent_schedules_user_two_weeks_url = "/users/me/respondent/current_events"

    schedule_url = f"{applet_detail_url}/events"
    schedule_import_url = f"{applet_detail_url}/events/import"
    schedule_create_individual = f"{applet_detail_url}/events/individual/{{respondent_id}}"

    delete_user_url = f"{applet_detail_url}/events/delete_individual/{{respondent_id}}"
    remove_ind_url = f"{applet_detail_url}/events/remove_individual/{{respondent_id}}"

    schedule_detail_url = f"{applet_detail_url}/events/{{event_id}}"

    count_url = "applets/{applet_id}/events/count"

    public_events_url = "public/applets/{key}/events"

    async def test_schedule_create_with_equal_start_end_time(self, client: TestClient, applet: AppletFull):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "activity_id": str(applet.activities[0].id),
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
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        assert response.status_code == 422

    async def test_schedule_create_with_activity(self, client: TestClient, applet: AppletFull):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "activity_id": str(applet.activities[0].id),
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
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        assert response.status_code == 201
        event = response.json()["result"]
        assert event["startTime"] == create_data["start_time"]
        assert event["activityId"] == create_data["activity_id"]

    async def test_schedule_create_with_respondent_id(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "respondent_id": str(lucy.id),
            "activity_id": str(applet.activities[0].id),
            "flow_id": None,
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )

        assert response.status_code == 201
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    async def test_schedule_create_with_flow(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )

        assert response.status_code == 201
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]
        assert event["flowId"] == create_data["flow_id"]

    async def test_schedule_get_all(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(self.schedule_url.format(applet_id=applet.id))

        assert response.status_code == 200
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
            "respondent_id": str(lucy.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )

        assert response.status_code == 201

        response = await client.get(self.schedule_url.format(applet_id=applet.id))

        assert response.status_code == 200
        events = response.json()["result"]
        assert len(events) == events_count

        response = await client.get(self.schedule_url.format(applet_id=applet.id) + f"?respondentId={lucy.id}")

        assert response.status_code == 200
        events = response.json()["result"]
        assert len(events) == 1

    # async def test_public_schedule_get_all(self, client: TestClient):
    #     response = await client.get(self.public_events_url.format(key="51857e10-6c05-4fa8-a2c8-725b8c1a0aa6"))

    #     assert response.status_code == 200
    #     events = response.json()["result"]
    #     assert isinstance(events, dict)

    async def test_schedule_get_detail(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event_id,
            )
        )

        assert response.status_code == 200
        event = response.json()["result"]
        assert event["respondentId"] == create_data["respondent_id"]

    async def test_schedule_delete_all(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.delete(self.schedule_url.format(applet_id=applet.id))
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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        assert response.status_code == 201

        response = await client.delete(self.schedule_url.format(applet_id=applet.id))

        assert response.status_code == 204

    async def test_schedule_delete_detail(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

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
            "respondent_id": str(lucy.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        event = response.json()["result"]

        response = await client.delete(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event["id"],
            )
        )

        assert response.status_code == 204

    async def test_schedule_update_with_equal_start_end_time(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "respondent_id": str(lucy.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
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
            self.schedule_url.format(applet_id=applet.id),
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
                applet_id=applet.id,
                event_id=event["id"],
            ),
            data=update_data,
        )
        assert response.status_code == 422

    async def test_schedule_update(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
            "respondent_id": str(lucy.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
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
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        event = response.json()["result"]
        create_data.pop("activity_id")
        create_data.pop("flow_id")
        create_data.pop("respondent_id")

        create_data["notification"]["notifications"] = [  # type: ignore[index]
            {
                "trigger_type": "RANDOM",
                "from_time": "08:30:00",
                "to_time": "08:40:00",
            },
        ]
        create_data["notification"]["reminder"] = {  # type: ignore[index]
            "activity_incomplete": 2,
            "reminder_time": "08:40:00",
        }

        response = await client.put(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event["id"],
            ),
            data=create_data,
        )
        assert response.status_code == 200

        event = response.json()["result"]

        assert (
            event["notification"]["reminder"]["reminderTime"]
            == create_data["notification"]["reminder"]["reminder_time"]  # type: ignore[index]
        )

    async def test_count(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(self.count_url.format(applet_id=applet.id))
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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )

        assert response.status_code == 201

        create_data["activity_id"] = str(applet.activities[0].id)
        create_data["flow_id"] = None
        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )

        assert response.status_code == 201

        response = await client.get(
            self.count_url.format(applet_id=applet.id),
        )

        assert response.status_code == 200

        result = response.json()["result"]

        assert isinstance(result["activityEvents"], list)
        assert isinstance(result["flowEvents"], list)

    async def test_schedule_delete_user(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.delete(
            self.delete_user_url.format(
                applet_id=applet.id,
                respondent_id=str(user.id),
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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event_id,
            )
        )

        assert response.status_code == 200
        assert response.json()["result"]["respondentId"] == create_data["respondent_id"]

        response = await client.delete(
            self.delete_user_url.format(
                applet_id=applet.id,
                respondent_id=str(user.id),
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event_id,
            )
        )
        assert response.status_code == 404

    async def test_schedules_get_user_all(self, client: TestClient):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(self.schedule_user_url)

        assert response.status_code == 200
        # one for activity and one for activity flow
        assert response.json()["count"] == 2

    async def test_respondent_schedules_get_user_two_weeks(self, client: TestClient, applet: AppletFull):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(self.erspondent_schedules_user_two_weeks_url)

        assert response.status_code == 200
        assert response.json()["count"] == 1
        result = response.json()["result"]
        keys = result[0]["events"][0].keys()
        assert set(keys) == {
            "id",
            "entityId",
            "availability",
            "selectedDate",
            "timers",
            "availabilityType",
            "notificationSettings",
        }

    async def test_schedule_get_user_by_applet(self, client: TestClient, applet: AppletFull):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(self.schedule_detail_user_url.format(applet_id=applet.id))
        assert response.status_code == 200

    async def test_schedule_remove_individual(self, client: TestClient, applet: AppletFull, user: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.delete(
            self.remove_ind_url.format(
                applet_id=applet.id,
                respondent_id=str(user.id),
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
            "respondent_id": str(user.id),
            "activity_id": None,
            "flow_id": str(applet.activity_flows[0].id),
        }

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=create_data,
        )
        event_id = response.json()["result"]["id"]

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event_id,
            )
        )

        assert response.status_code == 200
        assert response.json()["result"]["respondentId"] == create_data["respondent_id"]

        response = await client.delete(
            self.remove_ind_url.format(
                applet_id=applet.id,
                respondent_id=str(user.id),
            )
        )

        assert response.status_code == 204

        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=event_id,
            )
        )
        assert response.status_code == 404

    async def test_schedule_import(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
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
                "respondent_id": str(lucy.id),
                "activity_id": str(applet.activities[0].id),
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
                "respondent_id": str(lucy.id),
                "activity_id": str(applet.activities[0].id),
                "flow_id": None,
            },
        ]

        response = await client.post(
            self.schedule_import_url.format(applet_id=applet.id),
            data=create_data,  # type: ignore[arg-type]
        )

        assert response.status_code == 201
        events = response.json()["result"]
        assert len(events) == 2
        assert events[0]["respondentId"] == create_data[0]["respondent_id"]

    async def test_schedule_create_individual(self, client: TestClient, applet: AppletFull, lucy: User):
        await client.login(self.login_url, "user@example.com", "Test1234!")
        response = await client.post(
            self.schedule_create_individual.format(
                applet_id=applet.id,
                respondent_id=str(lucy.id),
            ),
        )
        assert response.status_code == 201

        events = response.json()["result"]
        assert len(events) == 2
        assert events[0]["respondentId"] == str(lucy.id)
