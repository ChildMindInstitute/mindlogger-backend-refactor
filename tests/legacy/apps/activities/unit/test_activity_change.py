import datetime
import uuid

import pytest
from pytest import FixtureRequest

from apps.activities.domain.activity_history import ActivityHistoryFull
from apps.activities.domain.scores_reports import (
    CalculationType,
    ReportType,
    Score,
    ScoresAndReports,
    Section,
    Subscale,
    SubscaleCalculationType,
    SubscaleItem,
    SubscaleItemType,
    SubscaleSetting,
)
from apps.activities.services.activity_change import ActivityChangeService
from apps.shared.enums import Language


@pytest.fixture
def activity_history_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def old_version() -> str:
    return "1.0.0"


@pytest.fixture
def new_version() -> str:
    return "2.0.0"


@pytest.fixture
def old_applet_id(old_version: str) -> str:
    return f"00000000-0000-0000-0000-000000000000_{old_version}"


@pytest.fixture
def new_applet_id(new_version: str) -> str:
    return f"00000000-0000-0000-0000-000000000000_{new_version}"


@pytest.fixture
def activity_change_service(old_version, new_version) -> ActivityChangeService:
    return ActivityChangeService(old_version, new_version)


@pytest.fixture
def old_id_version(activity_history_id: uuid.UUID, old_version: str) -> str:
    return f"{activity_history_id}_{old_version}"


@pytest.fixture
def new_id_version(activity_history_id: uuid.UUID, new_version: str) -> str:
    return f"{activity_history_id}_{new_version}"


@pytest.fixture
def score() -> Score:
    return Score(
        type=ReportType.score,
        name="testscore",
        id=str(uuid.uuid4()),
        calculation_type=CalculationType.SUM,
    )


@pytest.fixture
def section() -> Section:
    return Section(type=ReportType.section, name="testsection")


@pytest.fixture
def subscale() -> Subscale:
    return Subscale(
        name="test",
        scoring=SubscaleCalculationType.AVERAGE,
        items=[SubscaleItem(name="subscale_item", type=SubscaleItemType.ITEM)],
    )


@pytest.fixture
def subscale_setting(subscale: Subscale) -> SubscaleSetting:
    return SubscaleSetting(
        calculate_total_score=SubscaleCalculationType.AVERAGE,
        subscales=[subscale],
    )


@pytest.fixture
def scores_and_reports(score: Score, section: Section) -> ScoresAndReports:
    return ScoresAndReports(
        generate_report=True,
        show_score_summary=True,
        reports=[score, section],
    )


@pytest.fixture
def old_activity(activity_history_id: uuid.UUID, old_applet_id: str, old_id_version: str) -> ActivityHistoryFull:
    return ActivityHistoryFull(
        id=activity_history_id,
        applet_id=old_applet_id,
        id_version=old_id_version,
        name="testname",
        description=dict(en=""),
        splash_screen="",
        image="",
        show_all_at_once=False,
        is_skippable=False,
        is_reviewable=False,
        response_is_editable=False,
        order=1,
        created_at=datetime.datetime.now(datetime.UTC),
        is_hidden=False,
    )


@pytest.fixture
def new_activity(activity_history_id: uuid.UUID, new_applet_id: str, new_version: str) -> ActivityHistoryFull:
    return ActivityHistoryFull(
        id=activity_history_id,
        applet_id=new_applet_id,
        id_version=new_version,
        name="testname",
        description=dict(en=""),
        splash_screen="",
        image="",
        show_all_at_once=False,
        is_skippable=False,
        is_reviewable=False,
        response_is_editable=False,
        order=1,
        created_at=datetime.datetime.now(datetime.UTC),
        is_hidden=False,
    )


def test_initial_activity_activity_changes(
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    initial_changes = [
        "Activity Name was set to testname",
        "Activity Order was set to 1",
        "Show all questions at once was disabled",
        "Allow to skip all items was disabled",
        "Turn the Activity to the Reviewer dashboard assessment was disabled",
        "Disable the respondent's ability to change the response was disabled",
        "Activity Visibility was enabled",
    ]
    changes = activity_change_service.get_changes_insert(new_activity)
    assert len(changes) == len(initial_changes)
    assert set(changes) == set(changes)


def test_initial_activity_hidden_activity_change(
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.is_hidden = True
    changes = activity_change_service.get_changes_insert(new_activity)
    assert changes
    assert "Activity Visibility was disabled" in changes


def test_initial_activity_bool_value_is_enabled(
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.show_all_at_once = True
    changes = activity_change_service.get_changes_insert(new_activity)
    assert changes
    assert "Show all questions at once was enabled" in changes


def test_initial_activity_description_was_set(
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.description = {Language.ENGLISH: "HELLO"}
    changes = activity_change_service.get_changes_insert(new_activity)
    assert changes
    assert "Activity Description was set to HELLO" in changes


@pytest.mark.parametrize(
    "fixture_name, exp_changes",
    (
        (
            "scores_and_reports",
            [
                "Scores & Reports: Generate Report was enabled",
                "Scores & Reports: Show Score Summary was enabled",
                "Scores & Reports: Score testscore was added",
                "Scores & Reports: Section testsection was added",
            ],
        ),
        (
            "subscale_setting",
            [
                "Subscale Configuration: Calculate total score was added",
                "Subscale Configuration: Subscale test was added",
            ],
        ),
    ),
)
def test_initial_activity_complex_fields_are_set(
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
    request: FixtureRequest,
    fixture_name: str,
    exp_changes: list[str],
):
    fixture = request.getfixturevalue(fixture_name)
    # We can use fixture name like attribute
    setattr(new_activity, fixture_name, fixture)
    changes = activity_change_service.get_changes_insert(new_activity)
    for change in exp_changes:
        assert change in changes


def test_new_activity_version_no_changes(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert not changes


def test_new_activity_version_is_hidden(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.is_hidden = True
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Activity Visibility was disabled"


def test_new_activity_version_bool_field_enabled(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.show_all_at_once = True
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Show all questions at once was enabled"


def test_new_activity_order_was_changed(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.order = 2
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Activity Order was changed to 2"


def test_new_activity_description_was_set(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    new_activity.description = {Language.ENGLISH: "BOOM"}
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Activity Description was set to BOOM"


def test_new_activity_description_was_changed(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
):
    old_activity.description = {Language.ENGLISH: "old"}
    new_activity.description = {Language.ENGLISH: "new"}
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Activity Description was changed to new"


def test_new_activity_scores_and_reports_is_none(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
    scores_and_reports: ScoresAndReports,
):
    old_activity.scores_and_reports = scores_and_reports
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Scores & Reports option was removed"


def test_new_activity_scores_and_reports_was_removed(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
    scores_and_reports: ScoresAndReports,
):
    old_activity.scores_and_reports = scores_and_reports
    # This is most realistic way
    new_activity.scores_and_reports = ScoresAndReports(generate_report=False, show_score_summary=False, reports=[])
    exp_changes = [
        "Scores & Reports: Generate Report was disabled",
        "Scores & Reports: Show Score Summary was disabled",
        "Scores & Reports: Score testscore was removed",
        "Scores & Reports: Section testsection was removed",
    ]
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == len(exp_changes)
    assert set(changes) == set(exp_changes)


def test_new_activity_subscale_setting_is_none(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
    subscale_setting: SubscaleSetting,
):
    old_activity.subscale_setting = subscale_setting
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == 1
    assert changes[0] == "Subscale Setting option was removed"


def test_new_activity_subscale_setting_was_removed(
    old_activity: ActivityHistoryFull,
    new_activity: ActivityHistoryFull,
    activity_change_service: ActivityChangeService,
    subscale_setting: SubscaleSetting,
):
    old_activity.subscale_setting = subscale_setting
    # This is most realistic way
    new_activity.subscale_setting = SubscaleSetting(subscales=list(), calculate_total_score=None)
    exp_changes = [
        "Subscale Configuration: Calculate total score was removed",
        "Subscale Configuration: Subscale test was removed",
    ]
    changes = activity_change_service.get_changes_update(old_activity, new_activity)
    assert len(changes) == len(exp_changes)
    assert set(changes) == set(exp_changes)
