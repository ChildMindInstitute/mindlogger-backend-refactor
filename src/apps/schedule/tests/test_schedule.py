import datetime
import http
import logging
import uuid

import pytest
from firebase_admin.exceptions import NotFoundError as FireBaseNotFoundError
from pytest import FixtureRequest, LogCaptureFixture
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.answers.errors import UserDoesNotHavePermissionError
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.errors import AppletNotFoundError
from apps.applets.service.applet import AppletService
from apps.schedule.crud.events import EventCRUD
from apps.schedule.crud.user_device_events_history import UserDeviceEventsHistoryCRUD
from apps.schedule.domain import constants
from apps.schedule.domain.constants import EventType
from apps.schedule.domain.schedule import (
    EventRequest,
    EventUpdate,
    EventUpdateRequest,
    Notification,
    NotificationSettingRequest,
    PeriodicityRequest,
    PublicEvent,
    ReminderSettingRequest,
)
from apps.schedule.errors import (
    AccessDeniedToApplet,
    ActivityOrFlowNotFoundError,
    EventAlwaysAvailableExistsError,
    StartEndTimeEqualError,
)
from apps.schedule.service.schedule import ScheduleService
from apps.schedule.tests.unit.domain.test_schedule_request_data import event_monthly_data
from apps.shared.enums import Language
from apps.shared.test.client import TestClient
from apps.shared.util import assert_not_none
from apps.users.domain import User, UserDeviceCreate
from apps.users.errors import UserNotFound
from apps.users.services.user_device import UserDeviceService
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.utility import FCMNotificationTest


def _get_number_default_events(applet: AppletFull) -> int:
    return len([i for i in applet.activities if not i.is_reviewable]) + len(applet.activity_flows)


@pytest.fixture
async def device_lucy(lucy: User, session: AsyncSession) -> str:
    device_id = "lucy device"
    service = UserDeviceService(session, lucy.id)
    await service.add_device(UserDeviceCreate(device_id=device_id))
    return device_id


@pytest.fixture
async def device_user(user: User, session: AsyncSession) -> str:
    device_id = "user device"
    service = UserDeviceService(session, user.id)
    await service.add_device(UserDeviceCreate(device_id=device_id))
    return device_id


@pytest.fixture
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


@pytest.fixture
async def applet(session: AsyncSession, user: User, applet_data: AppletCreate) -> AppletFull:
    srv = AppletService(session, user.id)
    applet = await srv.create(applet_data)
    return applet


@pytest.fixture
async def minimal_applet(session: AsyncSession, user: User, applet_minimal_data: AppletCreate) -> AppletFull:
    srv = AppletService(session, user.id)
    applet = await srv.create(applet_minimal_data)
    return applet


@pytest.fixture
async def applet_default_events(session: AsyncSession, applet: AppletFull) -> list[PublicEvent]:
    srv = ScheduleService(session)
    events = await srv.get_all_schedules(applet_id=applet.id)
    return events


@pytest.fixture
async def minimal_applet_default_event(session: AsyncSession, minimal_applet: AppletFull) -> PublicEvent:
    srv = ScheduleService(session)
    events = await srv.get_all_schedules(applet_id=minimal_applet.id)
    return events[0]


@pytest.fixture
async def applet_lucy_respondent(session: AsyncSession, applet: AppletFull, user: User, lucy: User) -> AppletFull:
    await UserAppletAccessService(session, user.id, applet.id).add_role(lucy.id, Role.RESPONDENT)
    return applet


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom) -> AppletFull:
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
def event_daily_data(applet: AppletFull) -> EventRequest:
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=1)
    return EventRequest(
        activity_id=applet.activities[0].id,
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=constants.PeriodicityType.DAILY,
            start_date=datetime.date.today(),
            end_date=end_date,
            selected_date=None,
        ),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        access_before_schedule=False,
        one_time_completion=None,
        notification=None,
        timer=None,
        timer_type=constants.TimerType.NOT_SET,
    )

@pytest.fixture
def event_monthly_data(applet: AppletFull, lucy: User) -> EventRequest:
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=30)
    return EventRequest(
        activity_id=None,#applet.activities[0].id,
        flow_id=str(applet.activity_flows[0].id),
        respondent_id=lucy.id,
        periodicity=PeriodicityRequest(
            type=constants.PeriodicityType.MONTHLY,
            start_date=start_date,
            end_date=end_date,
            selected_date=start_date,
        ),        
        start_time=datetime.time(8, 0),
        end_time=datetime.time(11, 0),         
        access_before_schedule= True,
        one_time_completion=True,
        notification=None,
        timer=None,
        timer_type=constants.TimerType.NOT_SET,
    )

@pytest.fixture
def event_daily_flow_data(applet: AppletFull, event_daily_data: EventRequest) -> EventRequest:
    data = event_daily_data.dict()
    data["activity_id"] = None
    data["flow_id"] = str(applet.activity_flows[0].id)
    model = EventRequest(**data)
    return model


@pytest.fixture
def event_daily_data_update(event_daily_data: EventRequest) -> EventUpdateRequest:
    data = event_daily_data.dict()
    del data["respondent_id"]
    del data["activity_id"]
    del data["flow_id"]
    return EventUpdateRequest(**data)


@pytest.fixture
async def daily_event(session: AsyncSession, applet: AppletFull, event_daily_data: EventRequest) -> PublicEvent:
    service = ScheduleService(session)
    schedule = await service.create_schedule(event_daily_data, applet.id)
    return schedule


@pytest.fixture
async def daily_event_individual_lucy(
    session: AsyncSession, applet_lucy_respondent: AppletFull, event_daily_data: EventRequest, lucy: User
) -> PublicEvent:
    data = event_daily_data.copy(deep=True)
    data.respondent_id = lucy.id
    service = ScheduleService(session)
    schedule = await service.create_schedule(data, applet_lucy_respondent.id)
    return schedule


@pytest.fixture
def notification() -> NotificationSettingRequest:
    return NotificationSettingRequest(
        trigger_type=constants.NotificationTriggerType.FIXED,
        at_time=datetime.time(9, 0),
        from_time=None,
        to_time=None,
        order=None,
    )


@pytest.fixture
def reminder() -> ReminderSettingRequest:
    return ReminderSettingRequest(activity_incomplete=0, reminder_time=datetime.time(9, 0))


@pytest.fixture
async def daily_event_lucy_with_notification_and_reminder(
    session: AsyncSession,
    applet_lucy_respondent: AppletFull,
    event_daily_data: EventRequest,
    notification: NotificationSettingRequest,
    reminder: ReminderSettingRequest,
    lucy: User,
):
    data = event_daily_data.copy(deep=True)
    data.respondent_id = lucy.id
    data.notification = Notification(notifications=[notification], reminder=reminder)
    service = ScheduleService(session)
    schedule = await service.create_schedule(data, applet_lucy_respondent.id)
    return schedule


@pytest.mark.usefixtures("applet", "applet_lucy_respondent", "device_lucy", "device_user")
class TestSchedule:
    login_url = "/auth/login"
    applet_detail_url = "applets/{applet_id}"

    schedule_user_url = "users/me/events"
    schedule_detail_user_url = f"{schedule_user_url}/{{applet_id}}"

    respondent_schedules_user_two_weeks_url = "/users/me/respondent/current_events"

    schedule_url = f"{applet_detail_url}/events"
    schedule_import_url = f"{applet_detail_url}/events/import"
    schedule_create_individual = f"{applet_detail_url}/events/individual/{{respondent_id}}"

    delete_user_url = f"{applet_detail_url}/events/delete_individual/{{respondent_id}}"
    remove_ind_url = f"{applet_detail_url}/events/remove_individual/{{respondent_id}}"

    schedule_detail_url = f"{applet_detail_url}/events/{{event_id}}"

    count_url = "applets/{applet_id}/events/count"

    public_events_url = "public/applets/{key}/events"

    async def test_schedule_create_with_equal_start_end_time(
        self, client: TestClient, applet: AppletFull, event_daily_data: EventRequest, user: User
    ):
        client.login(user)
        data = event_daily_data.dict()
        data["start_time"] = data["end_time"]
        response = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == StartEndTimeEqualError.message

    async def test_schedule_create_with_activity(
        self, client: TestClient, applet: AppletFull, event_daily_data: EventRequest, user: User
    ):
        client.login(user)
        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=event_daily_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED
        event = response.json()["result"]
        assert event["startTime"] == str(event_daily_data.start_time)
        assert event["activityId"] == str(event_daily_data.activity_id)
        assert event["endTime"] == str(event_daily_data.end_time)
        assert not event["accessBeforeSchedule"]
        assert event["oneTimeCompletion"] is None
        assert event["timer"] is None
        assert event["timerType"] == constants.TimerType.NOT_SET
        assert event["periodicity"]["type"] == constants.PeriodicityType.DAILY
        assert event["periodicity"]["startDate"] == str(event_daily_data.periodicity.start_date)
        assert event["periodicity"]["endDate"] == str(event_daily_data.periodicity.end_date)
        assert event["periodicity"]["selectedDate"] is None
        assert event["respondentId"] is None
        assert event["flowId"] is None
        assert event["notification"] is None

    async def test_schedule_create_individual_event(
        self,
        client: TestClient,
        applet_lucy_respondent: AppletFull,
        lucy: User,
        event_daily_data: EventRequest,
        user: User,
    ):
        client.login(user)
        data = event_daily_data.copy(deep=True)
        data.respondent_id = lucy.id

        response = await client.post(
            self.schedule_url.format(applet_id=applet_lucy_respondent.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        event = response.json()["result"]
        assert event["respondentId"] == str(lucy.id)

    async def test_schedule_create_with_flow(
        self, client: TestClient, applet: AppletFull, user: User, event_daily_data: EventRequest
    ):
        client.login(user)
        client.login(user)
        data = event_daily_data.dict()
        data["flow_id"] = str(applet.activity_flows[0].id)
        data["activity_id"] = None

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        event = response.json()["result"]
        assert event["flowId"] == data["flow_id"]
        assert event["activityId"] is None

    async def test_schedule_get_all__only_default_events(self, client: TestClient, applet: AppletFull, user: User):
        client.login(user)
        response = await client.get(self.schedule_url.format(applet_id=applet.id))
        number_default_events = _get_number_default_events(applet)
        assert response.status_code == http.HTTPStatus.OK
        events = response.json()["result"]
        events_count = response.json()["count"]
        assert len(events) == events_count
        assert events_count == number_default_events
        for event in events:
            assert event["periodicity"]["type"] == constants.PeriodicityType.ALWAYS

    @pytest.mark.parametrize(
        "event_for, field_name, field_name_to_replace",
        (
            ("activities", "activity_id", "flow_id"),
            ("activity_flows", "flow_id", "activity_id"),
        ),
    )
    async def test_schedule_get_all_after_creating_new_event__default_event_replaced_with_scheduled_event(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        event_daily_data: EventRequest,
        event_for: str,
        field_name: str,
        field_name_to_replace: str,
    ):
        client.login(user)
        data = event_daily_data.dict()
        data[field_name] = getattr(applet, event_for)[0].id
        data[field_name_to_replace] = None
        number_of_events = _get_number_default_events(applet)

        response = await client.post(
            self.schedule_url.format(applet_id=applet.id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(self.schedule_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.OK
        events = response.json()["result"]
        # after creating event with scheduled access default events removed for this activity/activity_flow
        assert len(events) == number_of_events
        events_count = response.json()["count"]
        assert events_count == number_of_events

    @pytest.mark.parametrize(
        "user_fixture_name,num_individual_events",
        (
            ("user", 0),
            ("lucy", 1),
        ),
    )
    @pytest.mark.usefixtures("daily_event_individual_lucy")
    async def test_schedule_get_all_for_respondent(
        self,
        client: TestClient,
        applet: AppletFull,
        user_fixture_name: str,
        num_individual_events: int,
        request: FixtureRequest,
        user: User,
    ):
        client.login(user)
        respondent = request.getfixturevalue(user_fixture_name)
        response = await client.get(self.schedule_url.format(applet_id=applet.id) + f"?respondentId={respondent.id}")
        assert response.status_code == http.HTTPStatus.OK
        events = response.json()["result"]
        assert len(events) == num_individual_events
        events_count = response.json()["count"]
        assert events_count == num_individual_events

    async def test_public_schedule_get_all(self, client: TestClient, applet_one_with_public_link: AppletFull):
        response = await client.get(self.public_events_url.format(key=applet_one_with_public_link.link))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["appletId"] == str(applet_one_with_public_link.id)
        events = result["events"]
        # TODO: check response
        assert isinstance(events, list)

    async def test_schedule_get_detail(
        self, client: TestClient, applet: AppletFull, daily_event: PublicEvent, user: User
    ):
        client.login(user)

        response = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert response.status_code == http.HTTPStatus.OK
        event = response.json()["result"]
        assert event["startTime"] == str(daily_event.start_time)
        assert event["activityId"] == str(daily_event.activity_id)
        assert event["endTime"] == str(daily_event.end_time)
        assert not event["accessBeforeSchedule"]
        assert event["oneTimeCompletion"] is None
        assert event["timer"] is None
        assert event["timerType"] == constants.TimerType.NOT_SET
        assert event["periodicity"]["type"] == constants.PeriodicityType.DAILY
        assert event["periodicity"]["startDate"] == str(daily_event.periodicity.start_date)
        assert event["periodicity"]["endDate"] == str(daily_event.periodicity.end_date)
        assert event["periodicity"]["selectedDate"] is None
        assert event["respondentId"] is None
        assert event["flowId"] is None
        assert event["notification"] is None

    @pytest.mark.usefixtures("daily_event")
    async def test_schedule_delete_all(self, client: TestClient, applet: AppletFull, user: User):
        client.login(user)
        response = await client.delete(self.schedule_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.NO_CONTENT
        # Check that only default events exist
        response = await client.get(self.schedule_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.OK
        for event in response.json()["result"]:
            assert event["periodicity"]["type"] == constants.PeriodicityType.ALWAYS

    async def test_schedule_delete_specific_event(
        self, client: TestClient, applet: AppletFull, daily_event: PublicEvent, user: User
    ):
        client.login(user)
        response = await client.delete(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert response.status_code == http.HTTPStatus.NO_CONTENT
        # Check that only default events exist
        response = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_schedule_update_with_equal_start_end_time(
        self,
        client: TestClient,
        applet: AppletFull,
        daily_event: PublicEvent,
        event_daily_data_update: EventUpdateRequest,
        user: User,
    ):
        client.login(user)
        data = event_daily_data_update.dict()
        data["start_time"] = data["end_time"]
        response = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id), data=data
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == StartEndTimeEqualError.message

    async def test_schedule_update(
        self,
        client: TestClient,
        applet: AppletFull,
        daily_event: PublicEvent,
        event_daily_data_update: EventUpdateRequest,
        fcm_client: FCMNotificationTest,
        device_lucy: str,
        device_user: str,
        user: User,
    ):
        client.login(user)
        data = event_daily_data_update.copy(deep=True)
        data.start_time = datetime.time(0, 0)
        data.end_time = datetime.time(23, 0)

        response = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.OK
        event = response.json()["result"]
        assert event["startTime"] == str(data.start_time)
        assert event["endTime"] == str(data.end_time)
        # lucy (respondent) and user (owner and respondent)
        assert len(fcm_client.notifications) == 2
        assert device_lucy in fcm_client.notifications
        assert device_user in fcm_client.notifications

    async def test_count(self, client: TestClient, applet: AppletFull, user: User, event_daily_data: EventRequest):
        client.login(user)
        response = await client.get(self.count_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        # Default events which with type "ALWAYS" are not included
        assert not result["activityEvents"]
        assert not result["flowEvents"]
        event_for_activity = event_daily_data.copy(deep=True)
        response = await client.post(self.schedule_url.format(applet_id=applet.id), data=event_for_activity)
        assert response.status_code == http.HTTPStatus.CREATED

        event_for_flow = event_daily_data.dict()
        event_for_flow["flow_id"] = str(applet.activity_flows[0].id)
        event_for_flow["activity_id"] = None
        response = await client.post(self.schedule_url.format(applet_id=applet.id), data=event_for_flow)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(self.count_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert len(result["activityEvents"]) == 1
        activity_event = result["activityEvents"][0]
        assert activity_event["count"] == 1
        assert activity_event["activityId"] == str(applet.activities[0].id)
        assert activity_event["activityName"] == applet.activities[0].name
        assert len(result["flowEvents"]) == 1
        flow_event = result["flowEvents"][0]
        assert flow_event["count"] == 1
        assert flow_event["flowId"] == str(applet.activity_flows[0].id)
        assert flow_event["flowName"] == applet.activity_flows[0].name

    async def test_delete_user_events_in_individual_schedule__event_not_found(
        self, client: TestClient, applet: AppletFull, user: User
    ):
        client.login(user)
        response = await client.delete(
            self.delete_user_url.format(
                applet_id=applet.id,
                respondent_id=str(user.id),
            )
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_delete_user_events_in_individual_schedule(
        self, client: TestClient, applet: AppletFull, user: User, lucy: User, daily_event_individual_lucy: PublicEvent
    ):
        client.login(user)
        response = await client.get(
            self.schedule_detail_url.format(
                applet_id=applet.id,
                event_id=daily_event_individual_lucy.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        response = await client.delete(self.delete_user_url.format(applet_id=applet.id, respondent_id=str(lucy.id)))
        assert response.status_code == http.HTTPStatus.NO_CONTENT
        response = await client.get(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event_individual_lucy.id)
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_schedules_get_user_all(self, client: TestClient, user: User, applet: AppletFull):
        client.login(user)
        response = await client.get(self.schedule_user_url)
        num_events = _get_number_default_events(applet)
        assert response.status_code == http.HTTPStatus.OK
        # Default events
        assert response.json()["count"] == num_events

    async def test_respondent_schedules_get_user_two_weeks(self, client: TestClient, applet: AppletFull, user: User):
        client.login(user)

        response = await client.get(self.respondent_schedules_user_two_weeks_url)

        assert response.status_code == http.HTTPStatus.OK
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
            "version",
        }

    async def test_schedule_get_all_by_respondent_user__store_device_properties(
        self,
        client: TestClient,
        minimal_applet: AppletFull,
        user: User,
        session: AsyncSession,
        minimal_applet_default_event: PublicEvent,
    ):
        client.login(user)

        device_id = "elyVxFQMQVa9FoT5vv0nWJ:APA91bHmm-kHlHY_6M0gHD4AheTDcRpR9rvet5dr9dYTcs8RLJEHXBTzN7S7265jXL"
        "OKdE8zo5VmU9ALOuoHO1Tg-3OvWhw1CURSO6jB01TT9RYsDSLi7CQ"

        response = await client.get(
            url=self.respondent_schedules_user_two_weeks_url,
            headers={
                "Device-Id": device_id,
                "OS-Name": "android",
                "OS-Version": "13",
                "App-Version": "2025.01.1",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        device_records = await UserDeviceEventsHistoryCRUD(session).get_all_by_device_id(device_id=device_id)

        device_records_for_event = [
            record for record in device_records if record.event_id == minimal_applet_default_event.id
        ]

        assert len(device_records_for_event) == 1
        device_record = device_records_for_event[0]
        assert device_record.device_id == device_id
        assert device_record.os_name == "android"
        assert device_record.os_version == "13"
        assert device_record.app_version == "2025.01.1"
        assert device_record.event_id == minimal_applet_default_event.id
        assert device_record.event_version == minimal_applet_default_event.version

    async def test_schedule_get_all_by_respondent_user__store_device_properties_device_id_only(
        self,
        client: TestClient,
        minimal_applet: AppletFull,
        user: User,
        session: AsyncSession,
        minimal_applet_default_event: PublicEvent,
    ):
        client.login(user)

        device_id = "elyVxFQMQVa9FoT5vv0nWJ:APA91bHmm-kHlHY_6M0gHD4AheTDcRpR9rvet5dr9dYTcs8RLJEHXBTzN7S7265jXL"
        "OKdE8zo5VmU9ALOuoHO1Tg-3OvWhw1CURSO6jB01TT9RYsDSLi7CQ"

        response = await client.get(
            url=self.respondent_schedules_user_two_weeks_url,
            headers={"Device-Id": device_id},
        )

        assert response.status_code == http.HTTPStatus.OK

        device_records = await UserDeviceEventsHistoryCRUD(session).get_all_by_device_id(device_id=device_id)

        device_records_for_event = [
            record for record in device_records if record.event_id == minimal_applet_default_event.id
        ]

        assert len(device_records_for_event) == 1
        device_record = device_records_for_event[0]
        assert device_record.device_id == device_id
        assert device_record.event_id == minimal_applet_default_event.id
        assert device_record.event_version == minimal_applet_default_event.version
        assert device_record.os_name is None
        assert device_record.os_version is None
        assert device_record.app_version is None

    async def test_schedule_get_all_by_respondent_user__store_device_properties_no_device_id(
        self,
        client: TestClient,
        minimal_applet: AppletFull,
        user: User,
        session: AsyncSession,
        minimal_applet_default_event: PublicEvent,
    ):
        client.login(user)

        response = await client.get(url=self.respondent_schedules_user_two_weeks_url)

        assert response.status_code == http.HTTPStatus.OK

        device_records = await UserDeviceEventsHistoryCRUD(session).get_all()

        assert len(device_records) == 0

    async def test_schedule_get_all_by_respondent_user__store_device_properties_existing_record(
        self,
        client: TestClient,
        minimal_applet: AppletFull,
        user: User,
        session: AsyncSession,
        minimal_applet_default_event: PublicEvent,
    ):
        client.login(user)

        crud = UserDeviceEventsHistoryCRUD(session)

        device_id = "elyVxFQMQVa9FoT5vv0nWJ:APA91bHmm-kHlHY_6M0gHD4AheTDcRpR9rvet5dr9dYTcs8RLJEHXBTzN7S7265jXL"
        "OKdE8zo5VmU9ALOuoHO1Tg-3OvWhw1CURSO6jB01TT9RYsDSLi7CQ"

        existing_records = await crud.record_event_versions(
            user_id=user.id,
            device_id=device_id,
            event_versions=[(minimal_applet_default_event.id, assert_not_none(minimal_applet_default_event.version))],
            os_name="android",
            os_version="13",
            app_version="2025.01.1",
        )

        assert len(existing_records) == 1

        existing_record = existing_records[0]

        response = await client.get(
            url=self.respondent_schedules_user_two_weeks_url,
            # OS version and app version have changed
            headers={
                "Device-Id": device_id,
                "OS-Name": "android",
                "OS-Version": "14",
                "App-Version": "2025.02.1",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        device_records = await crud.get_all_by_device_id(device_id=device_id)

        device_records_for_event = [
            record for record in device_records if record.event_id == minimal_applet_default_event.id
        ]

        assert len(device_records_for_event) == 1
        device_record = device_records_for_event[0]
        assert device_record.device_id == device_id
        assert device_record.os_name == existing_record.os_name
        assert device_record.os_version == existing_record.os_version  # Has *not* been updated
        assert device_record.app_version == existing_record.app_version  # Has *not* been updated
        assert device_record.event_id == minimal_applet_default_event.id
        assert device_record.event_version == minimal_applet_default_event.version
        assert device_record.updated_at != existing_record.updated_at  # Has been updated

    async def test_schedule_get_all_by_respondent_user__store_device_properties_new_event_version(
        self,
        client: TestClient,
        minimal_applet: AppletFull,
        user: User,
        session: AsyncSession,
        minimal_applet_default_event: PublicEvent,
    ):
        client.login(user)

        crud = UserDeviceEventsHistoryCRUD(session)

        device_id = "elyVxFQMQVa9FoT5vv0nWJ:APA91bHmm-kHlHY_6M0gHD4AheTDcRpR9rvet5dr9dYTcs8RLJEHXBTzN7S7265jXL"
        "OKdE8zo5VmU9ALOuoHO1Tg-3OvWhw1CURSO6jB01TT9RYsDSLi7CQ"

        existing_records = await crud.record_event_versions(
            user_id=user.id,
            device_id=device_id,
            event_versions=[(minimal_applet_default_event.id, assert_not_none(minimal_applet_default_event.version))],
            os_name="android",
            os_version="13",
            app_version="2025.01.1",
        )

        assert len(existing_records) == 1

        existing_record = existing_records[0]

        # Update the event version
        updated_event = await EventCRUD(session).update(
            pk=minimal_applet_default_event.id,
            schema=EventUpdate(
                start_time=minimal_applet_default_event.start_time,
                end_time=minimal_applet_default_event.end_time,
                access_before_schedule=minimal_applet_default_event.access_before_schedule,
                one_time_completion=True,
                timer=minimal_applet_default_event.timer,
                timer_type=minimal_applet_default_event.timer_type,
                applet_id=minimal_applet.id,
                periodicity=minimal_applet_default_event.periodicity.type,
                start_date=minimal_applet_default_event.periodicity.start_date,
                end_date=minimal_applet_default_event.periodicity.end_date,
                selected_date=minimal_applet_default_event.periodicity.selected_date,
                event_type=EventType.ACTIVITY if minimal_applet_default_event.activity_id else EventType.FLOW,
                activity_id=minimal_applet_default_event.activity_id,
                activity_flow_id=minimal_applet_default_event.flow_id,
                user_id=None,
            ),
        )

        response = await client.get(
            url=self.respondent_schedules_user_two_weeks_url,
            # OS version and app version have changed
            headers={
                "Device-Id": device_id,
                "OS-Name": "android",
                "OS-Version": "14",
                "App-Version": "2025.02.1",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        device_records = await crud.get_all_by_device_id(device_id=device_id)

        device_records_for_event = [
            record for record in device_records if record.event_id == minimal_applet_default_event.id
        ]

        assert len(device_records_for_event) == 2

        device_record_1 = device_records_for_event[0]
        assert dict(device_record_1) == dict(existing_record)

        device_record_2 = device_records_for_event[1]
        assert device_record_2.device_id == device_id
        assert device_record_2.os_name == "android"
        assert device_record_2.os_version == "14"
        assert device_record_2.app_version == "2025.02.1"
        assert device_record_2.event_id == minimal_applet_default_event.id
        assert device_record_2.event_version == updated_event.version

    async def test_schedule_get_user_by_applet(self, client: TestClient, applet: AppletFull, user: User):
        client.login(user)

        response = await client.get(self.schedule_detail_user_url.format(applet_id=applet.id))
        assert response.status_code == http.HTTPStatus.OK

    async def test_schedule_create_individual(
        self, client: TestClient, applet: AppletFull, lucy: User, user: User, applet_default_events: list[PublicEvent]
    ):
        client.login(user)
        response = await client.post(
            self.schedule_create_individual.format(
                applet_id=applet.id,
                respondent_id=str(lucy.id),
            ),
        )
        assert response.status_code == http.HTTPStatus.CREATED

        events = response.json()["result"]
        assert len(events) == 2
        assert events[0]["respondentId"] == str(lucy.id)
        default_applet_events_ids_set = set(str(i.id) for i in applet_default_events)
        individual_default_events_ids_set = set(i["id"] for i in events)
        assert default_applet_events_ids_set != individual_default_events_ids_set
        for event in events:
            assert event["periodicity"]["type"] == constants.PeriodicityType.ALWAYS

    async def test_remove_individual_calendar__events_for_user_not_found(
        self, client: TestClient, applet: AppletFull, user: User
    ):
        client.login(user)
        response = await client.delete(self.remove_ind_url.format(applet_id=applet.id, respondent_id=str(user.id)))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_remove_individual_calendar(
        self, client: TestClient, applet: AppletFull, user: User, applet_default_events: list[PublicEvent]
    ):
        client.login(user)
        response = await client.post(self.schedule_create_individual.format(applet_id=applet.id, respondent_id=user.id))
        assert response.status_code == http.HTTPStatus.CREATED
        ids = [i["id"] for i in response.json()["result"]]

        response = await client.delete(self.remove_ind_url.format(applet_id=applet.id, respondent_id=str(user.id)))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        for id_ in ids:
            response = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=id_))
            assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_schedule_import(
        self, client: TestClient, applet: AppletFull, lucy: User, event_daily_data: EventRequest, user: User
    ):
        client.login(user)
        # Just create 3 events for import
        time_pairs_list = [("08:00:00", "09:00:00"), ("12:00:00", "13:00:00"), ("18:00:00", "19:00:00")]
        import_data = []
        for start_time, end_time in time_pairs_list:
            data = event_daily_data.dict()
            data["respondent_id"] = str(lucy.id)
            data["start_time"] = start_time
            data["end_time"] = end_time
            import_data.append(data)

        response = await client.post(
            self.schedule_import_url.format(applet_id=applet.id),
            data=import_data,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        events = response.json()["result"]
        assert len(events) == len(import_data)
        for act, exp in zip(events, import_data):
            assert act["startTime"] == exp["start_time"]
            assert act["endTime"] == exp["end_time"]

    async def test_create_schedule_events__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        mocker: MockerFixture,
        event_daily_data: EventRequest,
        caplog: LogCaptureFixture,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=event_daily_data)
        assert resp.status_code == http.HTTPStatus.CREATED
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_get_all_schedules_no_permissions(self, client: TestClient, applet: AppletFull, lucy: User):
        client.login(lucy)
        resp = await client.get(self.schedule_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == UserDoesNotHavePermissionError.message

    async def test_delete_all_schedule_events__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.delete(self.schedule_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_delete_event_by_id__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        daily_event: PublicEvent,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.delete(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_update_event__firefase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        daily_event: PublicEvent,
        event_daily_data_update: EventUpdateRequest,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id), data=event_daily_data_update
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_delete_individual_event_by_id__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        lucy: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        daily_event_individual_lucy: PublicEvent,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.delete(
            self.delete_user_url.format(
                applet_id=applet.id, event_id=daily_event_individual_lucy.id, respondent_id=lucy.id
            )
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_delete_individual_calendar__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        lucy: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        daily_event_individual_lucy: PublicEvent,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        resp = await client.delete(
            self.remove_ind_url.format(
                applet_id=applet.id, event_id=daily_event_individual_lucy.id, respondent_id=lucy.id
            )
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_create_individual_calendar__firebase_error_muted(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        lucy: User,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        event_daily_data: EventRequest,
    ):
        caplog.set_level(logging.ERROR)
        client.login(user)
        error_message = "device id not found"
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message=error_message),
        )
        data = event_daily_data.copy(deep=True)
        data.respondent_id = lucy.id
        resp = await client.post(
            self.schedule_create_individual.format(applet_id=applet.id, respondent_id=lucy.id), data=data
        )
        assert resp.status_code == http.HTTPStatus.CREATED
        assert caplog.messages
        assert caplog.messages[0] == error_message

    async def test_update_individual_event__notification_sent_to_the_individual_respondent(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        event_daily_data_update: EventUpdateRequest,
        daily_event_individual_lucy: PublicEvent,
        fcm_client: FCMNotificationTest,
        device_lucy: str,
    ):
        client.login(user)
        data = event_daily_data_update.copy(deep=True)
        data.start_time = datetime.time(0, 0)
        data.end_time = datetime.time(20, 0)
        resp = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event_individual_lucy.id), data=data
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert device_lucy in fcm_client.notifications
        assert len(fcm_client.notifications) == 1
        notification = fcm_client.notifications[device_lucy][0]
        assert "Your schedule has been changed, click to update." in notification

    async def test_delete_by_id_individual_event__notification_sent_to_the_individual_respondent(
        self,
        client: TestClient,
        applet: AppletFull,
        user: User,
        daily_event_individual_lucy: PublicEvent,
        fcm_client: FCMNotificationTest,
        device_lucy: str,
    ):
        client.login(user)
        resp = await client.delete(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event_individual_lucy.id)
        )
        assert resp.status_code == http.HTTPStatus.NO_CONTENT
        assert device_lucy in fcm_client.notifications
        assert len(fcm_client.notifications) == 1
        notification = fcm_client.notifications[device_lucy][0]
        assert "Your schedule has been changed, click to update." in notification

    async def test_create_event_with_notifications(
        self,
        client: TestClient,
        event_daily_data: EventRequest,
        notification: NotificationSettingRequest,
        user: User,
        applet: AppletFull,
    ):
        client.login(user)
        data = event_daily_data.copy(deep=True)
        data.notification = Notification(notifications=[notification])
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        notifications = resp.json()["result"]["notification"]["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["triggerType"] == notification.trigger_type
        assert notifications[0]["fromTime"] == notification.from_time
        assert notifications[0]["toTime"] == notification.to_time
        assert notifications[0]["atTime"] == str(notification.at_time)
        assert notifications[0]["order"] == 1

    async def test_create_event_with_reminder(
        self,
        client: TestClient,
        event_daily_data: EventRequest,
        reminder: ReminderSettingRequest,
        user: User,
        applet: AppletFull,
    ):
        client.login(user)
        data = event_daily_data.copy(deep=True)
        data.notification = Notification(reminder=reminder)
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp_reminder = resp.json()["result"]["notification"]["reminder"]
        assert resp_reminder["activityIncomplete"] == reminder.activity_incomplete
        assert resp_reminder["reminderTime"] == str(reminder.reminder_time)

    async def test_delete_all_schedules_twice(
        self,
        client: TestClient,
        user: User,
        applet: AppletFull,
    ):
        client.login(user)
        resp = await client.delete(self.schedule_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.NO_CONTENT

        resp = await client.delete(self.schedule_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.NO_CONTENT

    async def test_update_schedule__change_periodicity_from_scheduled_type_to_the_always(
        self,
        client: TestClient,
        user: User,
        daily_event: PublicEvent,
        applet: AppletFull,
        event_daily_data_update: EventUpdateRequest,
    ):
        # TODO
        client.login(user)
        data = event_daily_data_update.copy(deep=True)
        data.periodicity.type = constants.PeriodicityType.ALWAYS
        data.one_time_completion = False
        resp = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id), data=data
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["periodicity"]["type"] == constants.PeriodicityType.ALWAYS

        resp = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["periodicity"]["type"] == constants.PeriodicityType.ALWAYS

    async def test_update_schedule__add_notification(
        self,
        client: TestClient,
        user: User,
        daily_event: PublicEvent,
        applet: AppletFull,
        event_daily_data_update: EventUpdateRequest,
        notification: NotificationSettingRequest,
    ):
        # TODO
        client.login(user)
        data = event_daily_data_update.copy(deep=True)
        data.notification = Notification(notifications=[notification])
        resp = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id), data=data
        )
        assert resp.status_code == http.HTTPStatus.OK
        notifications = resp.json()["result"]["notification"]["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["triggerType"] == notification.trigger_type
        assert notifications[0]["fromTime"] == notification.from_time
        assert notifications[0]["toTime"] == notification.to_time
        assert notifications[0]["atTime"] == str(notification.at_time)
        assert notifications[0]["order"] == 1
        resp = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert resp.status_code == http.HTTPStatus.OK

        notifications = resp.json()["result"]["notification"]["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["triggerType"] == notification.trigger_type
        assert notifications[0]["fromTime"] == notification.from_time
        assert notifications[0]["toTime"] == notification.to_time
        assert notifications[0]["atTime"] == str(notification.at_time)
        assert notifications[0]["order"] == 1

    async def test_update_schedule__add_reminder(
        self,
        client: TestClient,
        user: User,
        daily_event: PublicEvent,
        applet: AppletFull,
        event_daily_data_update: EventUpdateRequest,
        reminder: ReminderSettingRequest,
    ):
        # TODO
        client.login(user)
        data = event_daily_data_update.copy(deep=True)
        data.notification = Notification(reminder=reminder)
        resp = await client.put(
            self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id), data=data
        )
        assert resp.status_code == http.HTTPStatus.OK
        resp_reminder = resp.json()["result"]["notification"]["reminder"]
        assert resp_reminder["activityIncomplete"] == reminder.activity_incomplete
        assert resp_reminder["reminderTime"] == str(reminder.reminder_time)

        resp = await client.get(self.schedule_detail_url.format(applet_id=applet.id, event_id=daily_event.id))
        assert resp.status_code == http.HTTPStatus.OK
        resp_reminder = resp.json()["result"]["notification"]["reminder"]
        assert resp_reminder["activityIncomplete"] == reminder.activity_incomplete
        assert resp_reminder["reminderTime"] == str(reminder.reminder_time)

    async def test_schedule_create_individual_event__respondent_does_not_have_access_to_the_applet(
        self,
        client: TestClient,
        applet_lucy_respondent: AppletFull,
        event_daily_data: EventRequest,
        tom: User,
        user: User,
    ):
        client.login(user)
        data = event_daily_data.copy(deep=True)
        data.respondent_id = tom.id
        resp = await client.post(
            self.schedule_url.format(applet_id=applet_lucy_respondent.id),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN

    async def test_schedule_create__no_valid_activity_id(
        self,
        client: TestClient,
        event_daily_data: EventRequest,
        applet: AppletFull,
        uuid_zero: uuid.UUID,
        user: User,
    ):
        client.login(user)
        data = event_daily_data.copy(deep=True)
        data.activity_id = uuid_zero
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == ActivityOrFlowNotFoundError.message

    async def test_schedule_create__no_valid_flow_id(
        self,
        client: TestClient,
        event_daily_data: EventRequest,
        applet: AppletFull,
        uuid_zero: uuid.UUID,
        user: User,
    ):
        client.login(user)
        data = event_daily_data.dict()
        data["activity_id"] = None
        data["flow_id"] = str(uuid_zero)
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == ActivityOrFlowNotFoundError.message

    async def test_user_get_events__user_does_not_have_access_to_the_applet(
        self, client: TestClient, tom: User, applet: AppletFull
    ):
        client.login(tom)
        resp = await client.get(self.schedule_detail_user_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AccessDeniedToApplet.message

    async def test_import_schedule__always_available_removed_old_events(
        self,
        client: TestClient,
        applet: AppletFull,
        event_daily_data: EventRequest,
        applet_default_events: list[PublicEvent],
        user: User,
    ):
        client.login(user)
        data = event_daily_data.dict()
        data["one_time_completion"] = False
        data["periodicity"]["type"] = constants.PeriodicityType.ALWAYS
        data["start_time"] = str(datetime.time(0, 0))
        data["end_time"] = str(datetime.time(23, 59))

        response = await client.post(self.schedule_import_url.format(applet_id=applet.id), data=[data])

        assert response.status_code == http.HTTPStatus.CREATED
        events = response.json()["result"]
        activity_event = next(i for i in applet_default_events if i.activity_id)
        assert len(events) == 1
        assert events[0]["id"] != str(activity_event.id)

    @pytest.mark.usefixtures("daily_event_lucy_with_notification_and_reminder")
    async def test_user_get_events__event_with_reminder_and_notifications(
        self,
        client: TestClient,
        lucy: User,
        applet: AppletFull,
        notification: NotificationSettingRequest,
        reminder: ReminderSettingRequest,
    ):
        client.login(lucy)
        resp = await client.get(self.schedule_detail_user_url.format(applet_id=applet.id))
        assert resp.status_code == http.HTTPStatus.OK
        events = resp.json()["result"]["events"]
        notif_settings = events[0]["notificationSettings"]
        assert notif_settings["notifications"][0]["triggerType"] == notification.trigger_type
        assert notif_settings["notifications"][0]["fromTime"] == notification.from_time
        assert notif_settings["notifications"][0]["toTime"] == notification.to_time
        assert notif_settings["notifications"][0]["atTime"]["hours"] == notification.at_time.hour  # type: ignore
        assert notif_settings["notifications"][0]["atTime"]["minutes"] == notification.at_time.minute  # type: ignore
        assert notif_settings["reminder"]["activityIncomplete"] == reminder.activity_incomplete
        assert notif_settings["reminder"]["reminderTime"]["hours"] == reminder.reminder_time.hour
        assert notif_settings["reminder"]["reminderTime"]["minutes"] == reminder.reminder_time.minute

    async def test_schedule_create__can_not_create_event_for_activity_always_avaiable(
        self, client: TestClient, applet: AppletFull, user: User, event_daily_data: EventRequest
    ):
        client.login(user)
        data = event_daily_data.dict()
        data["one_time_completion"] = False
        data["periodicity"]["type"] = constants.PeriodicityType.ALWAYS
        data["start_time"] = str(datetime.time(0, 0))
        data["end_time"] = str(datetime.time(23, 59))
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == EventAlwaysAvailableExistsError.message

    async def test_schedule_create__can_not_create_event_for_flow_always_avaiable(
        self, client: TestClient, applet: AppletFull, user: User, event_daily_data: EventRequest
    ):
        client.login(user)
        data = event_daily_data.dict()
        data["flow_id"] = str(applet.activity_flows[0].id)
        data["activity_id"] = None
        data["one_time_completion"] = False
        data["periodicity"]["type"] = constants.PeriodicityType.ALWAYS
        data["start_time"] = str(datetime.time(0, 0))
        data["end_time"] = str(datetime.time(23, 59))
        resp = await client.post(self.schedule_url.format(applet_id=applet.id), data=data)
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == EventAlwaysAvailableExistsError.message

    async def test_public_schedule__applet_is_not_public(self, client: TestClient, uuid_zero: uuid.UUID):
        resp = await client.get(self.public_events_url.format(key=uuid_zero))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == str(AppletNotFoundError(key="key", value=str(uuid_zero)))

    async def test_schedule_get_all_for_applet_and_user__user_does_not_exist(
        self,
        client: TestClient,
        applet: AppletFull,
        uuid_zero: uuid.UUID,
        user: User,
    ):
        client.login(user)
        resp = await client.get(self.schedule_url.format(applet_id=applet.id), query={"respondentId": uuid_zero})
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == UserNotFound.message

    async def test_coordinator_can_schedule_event(
        self,
        client: TestClient,  
        lucy: User,     
        applet_one_lucy_coordinator: AppletFull,        
        event_monthly_data: EventRequest,
  
    ):
        client.login(lucy)
        data = event_monthly_data.copy(deep=True)
        data.periodicity.type = constants.PeriodicityType.MONTHLY
        resp = await client.post(
            self.schedule_url.format(applet_id=applet_one_lucy_coordinator.id), data=data,
        ) 
        assert resp.status_code == 201
