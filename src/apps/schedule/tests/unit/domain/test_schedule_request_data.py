import datetime
import uuid
from typing import cast

import pytest
from pytest import FixtureRequest

from apps.schedule import errors
from apps.schedule.domain.constants import NotificationTriggerType, PeriodicityType, TimerType
from apps.schedule.domain.schedule import (
    EventRequest,
    HourMinute,
    Notification,
    NotificationSettingRequest,
    PeriodicityRequest,
    ReminderSettingRequest,
)
from apps.shared.exception import FieldError


@pytest.fixture
def event_always_data() -> EventRequest:
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.ALWAYS,
            start_date=None,
            end_date=None,
            selected_date=None,
        ),
        start_time=datetime.time(0, 0),
        end_time=datetime.time(23, 59),
        access_before_schedule=False,
        one_time_completion=False,
        notification=None,
        timer=None,
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def event_daily_data() -> EventRequest:
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=1)
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.DAILY,
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
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def event_once_data() -> EventRequest:
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.ONCE,
            start_date=None,
            end_date=None,
            selected_date=datetime.date.today(),
        ),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        access_before_schedule=False,
        one_time_completion=None,
        notification=None,
        timer=None,
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def event_weekly_data() -> EventRequest:
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=1)
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.WEEKLY,
            start_date=start_date,
            end_date=end_date,
            selected_date=start_date,
        ),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        access_before_schedule=False,
        one_time_completion=None,
        notification=None,
        timer=None,
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def event_weekdays_data() -> EventRequest:
    start_date = datetime.date(2024, 3, 25)
    end_date = start_date + datetime.timedelta(days=7)
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.WEEKDAYS,
            start_date=start_date,
            end_date=end_date,
            selected_date=None,
        ),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        access_before_schedule=False,
        one_time_completion=None,
        notification=None,
        timer=None,
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def event_monthly_data() -> EventRequest:
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=31)
    return EventRequest(
        activity_id=uuid.uuid4(),
        flow_id=None,
        respondent_id=None,
        periodicity=PeriodicityRequest(
            type=PeriodicityType.MONTHLY,
            start_date=start_date,
            end_date=end_date,
            selected_date=start_date,
        ),
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        access_before_schedule=False,
        one_time_completion=None,
        notification=None,
        timer=None,
        timer_type=TimerType.NOT_SET,
    )


@pytest.fixture
def notification_notifications_fixed() -> Notification:
    notif = NotificationSettingRequest(
        trigger_type=NotificationTriggerType.FIXED,
        at_time=datetime.time(9, 0),
        from_time=None,
        to_time=None,
        order=None,
    )
    return Notification(notifications=[notif], reminder=None)


@pytest.fixture
def notification_notifications_random() -> Notification:
    notif = NotificationSettingRequest(
        trigger_type=NotificationTriggerType.RANDOM,
        at_time=None,
        from_time=datetime.time(9, 0),
        to_time=datetime.time(10, 0),
        order=None,
    )
    return Notification(notifications=[notif], reminder=None)


@pytest.fixture
def notification_reminder() -> Notification:
    reminder = ReminderSettingRequest(activity_incomplete=0, reminder_time=datetime.time(9, 0))
    return Notification(reminder=reminder)


def test_event_request_activity_or_flow_required(event_daily_data: EventRequest):
    data = event_daily_data.dict()
    data["activity_id"] = None
    data["flow_id"] = None
    with pytest.raises(errors.ActivityOrFlowRequiredError):
        EventRequest(**data)


def test_event_request__both_activity_and_flow_are_provided(event_daily_data: EventRequest):
    data = event_daily_data.dict()
    data["activity_id"] = uuid.uuid4()
    data["flow_id"] = uuid.uuid4()
    with pytest.raises(errors.ActivityOrFlowRequiredError):
        EventRequest(**data)


def test_event_request_periodicity_always_one_time_completion_required(event_always_data: EventRequest):
    data = event_always_data.dict()
    data["one_time_completion"] = None
    with pytest.raises(errors.OneTimeCompletionCaseError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, field_name",
    (
        ("event_daily_data", "start_time"),
        ("event_daily_data", "end_time"),
        ("event_daily_data", "access_before_schedule"),
        ("event_once_data", "start_time"),
        ("event_once_data", "end_time"),
        ("event_once_data", "access_before_schedule"),
        ("event_weekly_data", "start_time"),
        ("event_weekly_data", "end_time"),
        ("event_weekly_data", "access_before_schedule"),
        ("event_weekdays_data", "start_time"),
        ("event_weekdays_data", "end_time"),
        ("event_weekdays_data", "access_before_schedule"),
        ("event_monthly_data", "start_time"),
        ("event_monthly_data", "end_time"),
        ("event_monthly_data", "access_before_schedule"),
    ),
)
def test_event_request_periodicity_not_always_no_required_fields(
    fixture_name: str, field_name: str, request: FixtureRequest
):
    event_request = request.getfixturevalue(fixture_name)
    data = event_request.dict()
    data[field_name] = None
    with pytest.raises(errors.StartEndTimeAccessBeforeScheduleCaseError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, out_of_range_time",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        ("event_daily_data", datetime.time(0, 0)),
        ("event_daily_data", datetime.time(23, 59)),
        ("event_once_data", datetime.time(0, 0)),
        ("event_once_data", datetime.time(23, 59)),
        ("event_weekly_data", datetime.time(0, 0)),
        ("event_weekly_data", datetime.time(23, 59)),
        ("event_weekdays_data", datetime.time(0, 0)),
        ("event_weekdays_data", datetime.time(23, 59)),
        ("event_monthly_data", datetime.time(0, 0)),
        ("event_monthly_data", datetime.time(23, 59)),
    ),
)
def test_event_request_with_fixed_notification__at_time_not_in_between_start_time_and_end_time(
    notification_notifications_fixed: Notification,
    fixture_name: str,
    request: FixtureRequest,
    out_of_range_time: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.notification = notification_notifications_fixed
    data = event_request.dict()
    data["notification"]["notifications"][0]["at_time"] = str(out_of_range_time)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, not_valid_from",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        ("event_daily_data", datetime.time(0, 0)),
        ("event_daily_data", datetime.time(23, 59)),
        ("event_once_data", datetime.time(0, 0)),
        ("event_once_data", datetime.time(23, 59)),
        ("event_weekly_data", datetime.time(0, 0)),
        ("event_weekly_data", datetime.time(23, 59)),
        ("event_weekdays_data", datetime.time(0, 0)),
        ("event_weekdays_data", datetime.time(23, 59)),
        ("event_monthly_data", datetime.time(0, 0)),
        ("event_monthly_data", datetime.time(23, 59)),
    ),
)
def test_event_request_with_random_notification__from_time_not_in_between_start_time_and_end_time(
    notification_notifications_random: Notification,
    fixture_name: str,
    request: FixtureRequest,
    not_valid_from: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.notification = notification_notifications_random
    data = event_request.dict()
    data["notification"]["notifications"][0]["from_time"] = str(not_valid_from)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, not_valid_to",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        ("event_daily_data", datetime.time(0, 0)),
        ("event_daily_data", datetime.time(23, 59)),
        ("event_once_data", datetime.time(0, 0)),
        ("event_once_data", datetime.time(23, 59)),
        ("event_weekly_data", datetime.time(0, 0)),
        ("event_weekly_data", datetime.time(23, 59)),
        ("event_weekdays_data", datetime.time(0, 0)),
        ("event_weekdays_data", datetime.time(23, 59)),
        ("event_monthly_data", datetime.time(0, 0)),
        ("event_monthly_data", datetime.time(23, 59)),
    ),
)
def test_event_request_with_random_notification__to_time_not_in_between_start_time_and_end_time(
    notification_notifications_random: Notification,
    fixture_name: str,
    request: FixtureRequest,
    not_valid_to: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.notification = notification_notifications_random
    data = event_request.dict()
    data["notification"]["notifications"][0]["to_time"] = str(not_valid_to)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, out_of_range_time",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        ("event_daily_data", datetime.time(0, 0)),
        ("event_daily_data", datetime.time(23, 59)),
        ("event_once_data", datetime.time(0, 0)),
        ("event_once_data", datetime.time(23, 59)),
        ("event_weekly_data", datetime.time(0, 0)),
        ("event_weekly_data", datetime.time(23, 59)),
        ("event_weekdays_data", datetime.time(0, 0)),
        ("event_weekdays_data", datetime.time(23, 59)),
        ("event_monthly_data", datetime.time(0, 0)),
        ("event_monthly_data", datetime.time(23, 59)),
    ),
)
def test_event_request_with_reminder_notification__at_time_not_in_between_start_time_and_end_time(
    notification_reminder: Notification,
    fixture_name: str,
    request: FixtureRequest,
    out_of_range_time: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.notification = notification_reminder
    data = event_request.dict()
    data["notification"]["reminder"]["reminder_time"] = str(out_of_range_time)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


def test_event_request__notification_reminder__reminder_time_can_not_be_none(
    notification_reminder: Notification, event_once_data: EventRequest
):
    event_request = event_once_data.copy(deep=True)
    event_request.notification = notification_reminder
    data = event_request.dict()
    data["notification"]["reminder"]["reminder_time"] = None
    with pytest.raises(ValueError):
        EventRequest(**data)


def test_event_request__notification_reminder__reminder_time_absent(
    notification_reminder: Notification, event_once_data: EventRequest
):
    event_request = event_once_data.copy(deep=True)
    event_request.notification = notification_reminder
    data = event_request.dict()
    del data["notification"]["reminder"]["reminder_time"]
    with pytest.raises(ValueError):
        EventRequest(**data)


def test_event_request_start_time_is_equal_end_time(event_once_data: EventRequest):
    data = event_once_data.dict()
    data["start_time"] = data["end_time"]
    with pytest.raises(errors.StartEndTimeEqualError):
        EventRequest(**data)


def test_notification__order_is_applied_automically():
    notif_one = NotificationSettingRequest(
        trigger_type=NotificationTriggerType.RANDOM,
        at_time=None,
        from_time=datetime.time(9, 0),
        to_time=datetime.time(9, 10),
        order=None,
    )
    notif_two = NotificationSettingRequest(
        trigger_type=NotificationTriggerType.RANDOM,
        at_time=None,
        from_time=datetime.time(9, 20),
        to_time=datetime.time(9, 30),
        order=None,
    )
    notification = Notification(notifications=[notif_one, notif_two], reminder=None)
    notification.notifications = cast(list, notification.notifications)
    for i, notif in enumerate(notification.notifications, start=1):
        assert i == notif.order


def test_notification_fixed__at_time_is_required():
    with pytest.raises(errors.AtTimeFieldRequiredError):
        NotificationSettingRequest(
            trigger_type=NotificationTriggerType.FIXED,
            at_time=None,
            from_time=None,
            to_time=None,
            order=None,
        )


@pytest.mark.parametrize("field_name", ("from_time", "to_time"))
def test_notification_random__from_end_time_can_not_be_none(field_name: str):
    data = {
        "trigger_type": NotificationTriggerType.RANDOM,
        "from_time": datetime.time(9, 0),
        "to_time": datetime.time(10, 0),
    }
    data[field_name] = None
    with pytest.raises(errors.FromTimeToTimeRequiredError):
        NotificationSettingRequest(**data)


@pytest.mark.parametrize("field_name", ("from_time", "to_time"))
def test_notification_random__from_end_time_are_required(field_name: str):
    data = {
        "trigger_type": NotificationTriggerType.RANDOM,
        "from_time": datetime.time(9, 0),
        "to_time": datetime.time(10, 0),
    }
    del data[field_name]
    with pytest.raises(errors.FromTimeToTimeRequiredError):
        NotificationSettingRequest(**data)


@pytest.mark.parametrize("periodicity_type", (PeriodicityType.ONCE, PeriodicityType.WEEKLY, PeriodicityType.MONTHLY))
def test_peridocity_selected_date_is_required(periodicity_type: PeriodicityType):
    with pytest.raises(errors.SelectedDateRequiredError):
        PeriodicityRequest(type=periodicity_type, start_date=None, end_date=None, selected_date=None)


@pytest.mark.parametrize(
    "field_name, not_valid_value, error",
    (("hours", 24, errors.HourRangeError), ("minutes", 60, errors.MinuteRangeError)),
)
def test_validate_not_valid_hour_minute(field_name: str, not_valid_value: int, error: FieldError):
    data = {"hours": 23, "minutes": 60}
    data[field_name] = not_valid_value
    with pytest.raises(error):  # type: ignore[call-overload]
        HourMinute(**data)


def test_timer_is_required_if_timer_type_is_not_no_set(event_daily_data: EventRequest):
    data = event_daily_data.dict()
    data["timer_type"] = TimerType.IDLE
    data["timer"] = None
    with pytest.raises(errors.TimerRequiredError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, not_valid_from",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        # So, end_time is changed so that it becomes cross-day
        ("event_daily_data", datetime.time(7, 0)),
        ("event_once_data", datetime.time(7, 0)),
        ("event_weekly_data", datetime.time(7, 0)),
        ("event_weekdays_data", datetime.time(7, 0)),
        ("event_monthly_data", datetime.time(7, 0)),
    ),
)
def test_event_cross_day_with_random_notification__from_time_not_in_between_start_time_and_end_time(
    notification_notifications_random: Notification,
    fixture_name: str,
    request: FixtureRequest,
    not_valid_from: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.end_time = datetime.time(3, 00)
    event_request.notification = notification_notifications_random
    data = event_request.dict()
    data["notification"]["notifications"][0]["from_time"] = str(not_valid_from)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, not_valid_to",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        # So, end_time is changed so that it becomes cross-day
        ("event_daily_data", datetime.time(7, 0)),
        ("event_once_data", datetime.time(7, 0)),
        ("event_weekly_data", datetime.time(7, 0)),
        ("event_weekdays_data", datetime.time(7, 0)),
        ("event_monthly_data", datetime.time(7, 0)),
    ),
)
def test_event_cross_day_with_random_notification__to_time_not_in_between_start_time_and_end_time(
    notification_notifications_random: Notification,
    fixture_name: str,
    request: FixtureRequest,
    not_valid_to: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.end_time = datetime.time(3, 00)
    event_request.notification = notification_notifications_random
    data = event_request.dict()
    data["notification"]["notifications"][0]["to_time"] = str(not_valid_to)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, out_of_range_time",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        # So, end_time is changed so that it becomes cross-day
        ("event_daily_data", datetime.time(7, 0)),
        ("event_once_data", datetime.time(7, 0)),
        ("event_weekly_data", datetime.time(7, 0)),
        ("event_weekdays_data", datetime.time(7, 0)),
        ("event_monthly_data", datetime.time(7, 0)),
    ),
)
def test_event_cross_day_with_fixed_notification__at_time_not_in_between_start_time_and_end_time(
    notification_notifications_fixed: Notification,
    fixture_name: str,
    request: FixtureRequest,
    out_of_range_time: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.end_time = datetime.time(3, 00)
    event_request.notification = notification_notifications_fixed
    data = event_request.dict()
    data["notification"]["notifications"][0]["at_time"] = str(out_of_range_time)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)


@pytest.mark.parametrize(
    "fixture_name, out_of_range_time",
    (
        # For all scheduled fixtures valid start_time/end_time = 9:00/10:00
        # So, end_time is changed so that it becomes cross-day
        ("event_daily_data", datetime.time(7, 0)),
        ("event_once_data", datetime.time(7, 0)),
        ("event_weekly_data", datetime.time(7, 0)),
        ("event_weekdays_data", datetime.time(7, 0)),
        ("event_monthly_data", datetime.time(7, 0)),
    ),
)
def test_event_cross_day_with_reminder_notification__at_time_not_in_between_start_time_and_end_time(
    notification_reminder: Notification,
    fixture_name: str,
    request: FixtureRequest,
    out_of_range_time: datetime.time,
):
    event_request = request.getfixturevalue(fixture_name)
    event_request.end_time = datetime.time(3, 00)
    event_request.notification = notification_reminder
    data = event_request.dict()
    data["notification"]["reminder"]["reminder_time"] = str(out_of_range_time)
    with pytest.raises(errors.UnavailableActivityOrFlowError):
        EventRequest(**data)
