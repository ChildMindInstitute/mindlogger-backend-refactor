import datetime
import uuid
from typing import cast

import pytest

from apps.applets.commands.applet_ema import RawRow, filter_events, is_last_day_of_month
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.version import INITIAL_VERSION


@pytest.fixture
def raw_row_always() -> RawRow:
    return RawRow(
        applet_id=uuid.uuid4(),
        date=datetime.date.today(),
        user_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        flow_name="flow_name",
        applet_version=INITIAL_VERSION,
        schedule_start_time=datetime.time(0, 0),
        schedule_end_time=datetime.time(23, 59),
        event_id=uuid.uuid4(),
        event_type=PeriodicityType.ALWAYS,
        start_date=None,
        end_date=None,
        selected_date=datetime.date.today(),
    )


@pytest.fixture
def raw_row_daily(raw_row_always: RawRow) -> RawRow:
    raw_row = raw_row_always.copy(deep=True)
    raw_row.event_type = PeriodicityType.DAILY
    raw_row.start_date = datetime.date(2024, 3, 4)
    raw_row.end_date = datetime.date(2024, 3, 6)
    return raw_row


@pytest.fixture
def raw_row_once(raw_row_always: RawRow) -> RawRow:
    raw_row = raw_row_always.copy(deep=True)
    raw_row.event_type = PeriodicityType.ONCE
    return raw_row


@pytest.fixture
def raw_row_weekdays(raw_row_always: RawRow) -> RawRow:
    raw_row = raw_row_always.copy(deep=True)
    raw_row.event_type = PeriodicityType.WEEKDAYS
    raw_row.start_date = datetime.date(2024, 3, 4)
    raw_row.end_date = datetime.date(2024, 3, 10)
    return raw_row


@pytest.fixture
def raw_row_weekly(raw_row_always: RawRow) -> RawRow:
    raw_row = raw_row_always.copy(deep=True)
    raw_row.event_type = PeriodicityType.WEEKLY
    raw_row.start_date = datetime.date(2024, 3, 4)
    raw_row.end_date = datetime.date(2024, 3, 17)
    return raw_row


@pytest.fixture
def raw_row_monthly(raw_row_always: RawRow) -> RawRow:
    raw_row = raw_row_always.copy(deep=True)
    raw_row.event_type = PeriodicityType.MONTHLY
    raw_row.start_date = datetime.date(2024, 3, 4)
    raw_row.end_date = datetime.date(2024, 4, 4)
    return raw_row


class TestEventsPeriodicityAlways:
    @pytest.mark.parametrize("date", (datetime.date(2024, 3, 4), datetime.date(2024, 3, 5)))
    def test_filter_events__events_are_always_in_schedule(self, raw_row_always: RawRow, date: datetime.date):
        raw_rows = [raw_row_always]
        filtered = filter_events(raw_rows, date)
        assert filtered


class TestEventsPeriodicityDaily:
    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 4), 1),
            (datetime.date(2024, 3, 5), 1),
            (datetime.date(2024, 3, 6), 1),
            # 6-th March is last day (end_date)
            (datetime.date(2024, 3, 7), 0),
        ),
    )
    def test_filter_events(self, raw_row_daily: RawRow, date: datetime.date, exp_len: int):
        raw_rows = [raw_row_daily]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    def test_filter_events__cross_day_event_day_after_end_date_is_included(self, raw_row_daily: RawRow):
        raw_row_daily.schedule_start_time = datetime.time(10, 0)
        raw_row_daily.schedule_end_time = datetime.time(5, 0)
        assert raw_row_daily.is_crossday_event
        raw_row_daily.end_date = cast(datetime.date, raw_row_daily.end_date)
        date = raw_row_daily.end_date + datetime.timedelta(days=1)
        raw_rows = [raw_row_daily]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == 1


class TestEventsPeriodicityOnce:
    @pytest.mark.parametrize("date", (datetime.date(2024, 3, 4), datetime.date(2024, 3, 5)))
    def test_filter_events(self, raw_row_once: RawRow, date: datetime.date):
        raw_row_once.selected_date = date
        raw_rows = [raw_row_once]
        filtered = filter_events(raw_rows, date)
        assert filtered

    def test_filter_events__not_in_schedule_date_past(self, raw_row_once: RawRow):
        run_date = datetime.date.today()
        raw_row_once.selected_date = run_date - datetime.timedelta(days=1)
        raw_rows = [raw_row_once]
        filtered = filter_events(raw_rows, run_date)
        assert not filtered

    def test_filter_events__not_in_schedule_date_future(self, raw_row_once: RawRow):
        run_date = datetime.date.today()
        raw_row_once.selected_date = run_date + datetime.timedelta(days=1)
        raw_rows = [raw_row_once]
        filtered = filter_events(raw_rows, run_date)
        assert not filtered

    @pytest.mark.parametrize(
        "delta_days, exp_len",
        (
            (0, 1),
            (1, 1),
            # Greater then end_date and not covered by crossday
            (2, 0),
        ),
    )
    def test_filter_events__cross_day_event(self, raw_row_once: RawRow, delta_days: int, exp_len: int):
        # Crossday event has '2' selected days. Selected day and following day.
        run_date = datetime.date.today() + datetime.timedelta(days=delta_days)
        raw_row_once.schedule_start_time = datetime.time(10, 0)
        raw_row_once.schedule_end_time = datetime.time(5, 0)
        assert raw_row_once.is_crossday_event
        raw_rows = [raw_row_once]
        filtered = filter_events(raw_rows, run_date)
        assert len(filtered) == exp_len


class TestEventsPeriodicityWeekdays:
    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 4), 1),
            (datetime.date(2024, 3, 5), 1),
            (datetime.date(2024, 3, 6), 1),
            (datetime.date(2024, 3, 7), 1),
            (datetime.date(2024, 3, 8), 1),
            (datetime.date(2024, 3, 9), 0),
            (datetime.date(2024, 3, 10), 0),
            (datetime.date(2024, 3, 11), 0),
        ),
    )
    def test_filter_events(self, raw_row_weekdays: RawRow, date: datetime.date, exp_len: int):
        raw_rows = [raw_row_weekdays]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 8), 1),
            # Cross day event, so Saturday is encluded
            (datetime.date(2024, 3, 9), 1),
            (datetime.date(2024, 3, 10), 0),
            (datetime.date(2024, 3, 11), 0),
        ),
    )
    def test_filter_events__cross_day(self, raw_row_weekdays: RawRow, date: datetime.date, exp_len: int):
        raw_row_weekdays.schedule_start_time = datetime.time(10, 0)
        raw_row_weekdays.schedule_end_time = datetime.time(5, 0)
        assert raw_row_weekdays.is_crossday_event
        raw_rows = [raw_row_weekdays]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len


class TestEventsPeriodicityWeekly:
    @pytest.mark.parametrize(
        "date, exp_len",
        (
            # Only Mondays
            (datetime.date(2024, 3, 4), 1),
            (datetime.date(2024, 3, 11), 1),
            (datetime.date(2024, 3, 10), 0),
            (datetime.date(2024, 3, 17), 0),
        ),
    )
    def test_filter_events(self, raw_row_weekly: RawRow, date: datetime.date, exp_len: int):
        raw_rows = [raw_row_weekly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            # Only Mondays and following day (Tuesday)
            (datetime.date(2024, 3, 4), 1),
            (datetime.date(2024, 3, 5), 1),
            (datetime.date(2024, 3, 11), 1),
            (datetime.date(2024, 3, 12), 1),
            (datetime.date(2024, 3, 10), 0),
            (datetime.date(2024, 3, 17), 0),
            # We don't have event, because start_date and end_date weekdays are not the same
            (datetime.date(2024, 3, 18), 0),
        ),
    )
    def test_filter_events__cross_day__start_weekday_and_end_weekday_are_not_the_same(
        self, raw_row_weekly: RawRow, date: datetime.date, exp_len: int
    ):
        raw_row_weekly.schedule_start_time = datetime.time(10, 0)
        raw_row_weekly.schedule_end_time = datetime.time(5, 0)
        assert raw_row_weekly.is_crossday_event
        raw_rows = [raw_row_weekly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    def test_filter_events__cross_day__start_date_sunday(self, raw_row_weekly: RawRow):
        raw_row_weekly.start_date = datetime.date(2024, 3, 10)
        raw_row_weekly.end_date = datetime.date(2024, 3, 24)
        raw_row_weekly.schedule_start_time = datetime.time(10, 0)
        raw_row_weekly.schedule_end_time = datetime.time(5, 0)
        assert raw_row_weekly.is_crossday_event
        date = datetime.date(2024, 3, 17)
        raw_rows = [raw_row_weekly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == 1

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            # Sundays and Mondays
            (datetime.date(2024, 3, 10), 1),
            (datetime.date(2024, 3, 11), 1),
            (datetime.date(2024, 3, 17), 1),
            (datetime.date(2024, 3, 18), 1),
            (datetime.date(2024, 3, 24), 1),
            # We have event, because start_date and end_date weekdays are the same
            (datetime.date(2024, 3, 25), 1),
        ),
    )
    def test_filter_events__cross_day__start_weekday_and_end_weekday_are_the_same(
        self, raw_row_weekly: RawRow, date: datetime.date, exp_len: int
    ):
        raw_row_weekly.start_date = datetime.date(2024, 3, 10)
        raw_row_weekly.end_date = datetime.date(2024, 3, 24)
        raw_row_weekly.schedule_start_time = datetime.time(10, 0)
        raw_row_weekly.schedule_end_time = datetime.time(5, 0)
        raw_rows = [raw_row_weekly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len


class TestEventsPeriodicityMontly:
    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 4), 1),
            # end_date included
            (datetime.date(2024, 4, 4), 1),
            # greater then end_date
            (datetime.date(2024, 5, 4), 0),
        ),
    )
    def test_filter_events(self, raw_row_monthly: RawRow, date: datetime.date, exp_len: int):
        raw_rows = [raw_row_monthly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 4), 1),
            (datetime.date(2024, 3, 5), 1),
            # end_date included
            (datetime.date(2024, 4, 4), 1),
            # and following date after end_date
            (datetime.date(2024, 4, 5), 1),
            # greater then end_date
            (datetime.date(2024, 5, 4), 0),
        ),
    )
    def test_filter_events__cross_day(self, raw_row_monthly: RawRow, date: datetime.date, exp_len: int):
        raw_row_monthly.schedule_start_time = datetime.time(10, 0)
        raw_row_monthly.schedule_end_time = datetime.time(5, 0)
        assert raw_row_monthly.is_crossday_event
        raw_rows = [raw_row_monthly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    def test_filter_events__cross_day_event__start_date_and_end_date_not_the_same_month_day(
        self,
        raw_row_monthly: RawRow,
    ):
        raw_row_monthly.schedule_start_time = datetime.time(10, 0)
        raw_row_monthly.schedule_end_time = datetime.time(5, 0)
        assert raw_row_monthly.is_crossday_event
        raw_row_monthly.end_date = cast(datetime.date, raw_row_monthly.end_date)
        date = raw_row_monthly.end_date
        # Only if month day of end_date is less then months day of start_date is interesting,
        # because the same logic on UI
        raw_row_monthly.end_date -= datetime.timedelta(days=1)
        raw_rows = [raw_row_monthly]
        filtered = filter_events(raw_rows, date)
        assert not filtered

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 31), 1),
            # end_date included
            (datetime.date(2024, 4, 30), 1),
            # greater then end_date
            (datetime.date(2024, 5, 31), 0),
        ),
    )
    def test_filter_events__start_date_is_last_day_of_month(
        self, raw_row_monthly: RawRow, date: datetime.date, exp_len: int
    ):
        raw_row_monthly.start_date = datetime.date(2024, 3, 31)
        raw_row_monthly.end_date = datetime.date(2024, 4, 30)
        raw_rows = [raw_row_monthly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len

    @pytest.mark.parametrize(
        "date, exp_len",
        (
            (datetime.date(2024, 3, 31), 1),
            (datetime.date(2024, 4, 1), 1),
            # end_date included
            (datetime.date(2024, 4, 30), 1),
            # and following date after end_date
            (datetime.date(2024, 5, 1), 1),
            # greater then end_date
            (datetime.date(2024, 5, 31), 0),
        ),
    )
    def test_filter_events__cross_day_event__start_date_and_and_date_is_last_day_of_month(
        self, raw_row_monthly: RawRow, date: datetime.date, exp_len: int
    ):
        raw_row_monthly.start_date = datetime.date(2024, 3, 31)
        raw_row_monthly.end_date = datetime.date(2024, 4, 30)
        raw_row_monthly.schedule_start_time = datetime.time(10, 0)
        raw_row_monthly.schedule_end_time = datetime.time(5, 0)
        assert raw_row_monthly.is_crossday_event
        raw_rows = [raw_row_monthly]
        filtered = filter_events(raw_rows, date)
        assert len(filtered) == exp_len


@pytest.mark.parametrize(
    "date, exp_result",
    (
        (datetime.date(2023, 2, 27), False),
        (datetime.date(2023, 2, 28), True),
        (datetime.date(2024, 2, 28), False),
        (datetime.date(2024, 2, 29), True),
        (datetime.date(2024, 3, 30), False),
        (datetime.date(2024, 3, 31), True),
        (datetime.date(2024, 4, 29), False),
        (datetime.date(2024, 4, 30), True),
    ),
)
def test_is_last_day_of_month(date: datetime.date, exp_result: bool):
    act_result = is_last_day_of_month(date)
    assert act_result == exp_result
