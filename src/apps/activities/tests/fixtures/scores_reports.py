import pytest

from apps.activities.domain.conditional_logic import Match
from apps.activities.domain.conditions import ConditionType, EqualCondition, ValuePayload
from apps.activities.domain.scores_reports import (
    CalculationType,
    ReportType,
    Score,
    ScoreConditionalLogic,
    ScoresAndReports,
    Section,
    Subscale,
    SubscaleCalculationType,
    SubscaleItem,
    SubscaleItemType,
    SubscaleSetting,
)

SCORE_ID = "not_uuid_testscore"


@pytest.fixture
def score_conditional_logic() -> ScoreConditionalLogic:
    return ScoreConditionalLogic(
        name="test",
        id="not_uuid_test",
        match=Match.ALL,
        conditions=[
            EqualCondition(
                item_name=SCORE_ID,
                payload=ValuePayload(value=1),
                type=ConditionType.EQUAL,
            )
        ],
    )


@pytest.fixture
def score() -> Score:
    return Score(
        type=ReportType.score,
        name="testscore",
        id=SCORE_ID,
        calculation_type=CalculationType.SUM,
    )


@pytest.fixture
def section() -> Section:
    return Section(type=ReportType.section, name="testsection")


@pytest.fixture
def scores_and_reports(score: Score, section: Section) -> ScoresAndReports:
    return ScoresAndReports(
        generate_report=True,
        show_score_summary=True,
        reports=[score, section],
    )


@pytest.fixture
def subscale_item() -> SubscaleItem:
    return SubscaleItem(name="activity_item_1", type=SubscaleItemType.ITEM)


@pytest.fixture
def subscale(subscale_item: SubscaleItem) -> Subscale:
    return Subscale(
        name="test subscale name",
        scoring=SubscaleCalculationType.AVERAGE,
        items=[subscale_item],
    )


@pytest.fixture
def subscale_setting(subscale: Subscale) -> SubscaleSetting:
    return SubscaleSetting(
        calculate_total_score=SubscaleCalculationType.AVERAGE,
        subscales=[subscale],
    )
