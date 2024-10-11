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
    SectionConditionalLogic,
    Subscale,
    SubscaleCalculationType,
    SubscaleItem,
    SubscaleItemType,
    SubScaleLookupTable,
    SubscaleSetting,
    TotalScoreTable,
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
def score_with_subcale() -> Score:
    return Score(
        type=ReportType.score,
        name="testscore type score",
        id=SCORE_ID,
        calculation_type=CalculationType.SUM,
        scoring_type="score",
        subscale_name="subscale type score",
    )


@pytest.fixture
def score_with_subcale_raw() -> Score:
    return Score(
        type=ReportType.score,
        name="testscore type score",
        id=SCORE_ID,
        calculation_type=CalculationType.SUM,
        scoring_type="raw_score",
        subscale_name=None,
    )


@pytest.fixture
def section_conditional_logic() -> SectionConditionalLogic:
    return SectionConditionalLogic(
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
def scores_and_reports_raw_score(score_with_subcale_raw: Score, section: Section) -> ScoresAndReports:
    return ScoresAndReports(
        generate_report=True,
        show_score_summary=True,
        reports=[score_with_subcale_raw, section],
    )


@pytest.fixture
def subscale_item() -> SubscaleItem:
    return SubscaleItem(name="activity_item_1", type=SubscaleItemType.ITEM)


@pytest.fixture
def subscale(subscale_item: SubscaleItem) -> Subscale:
    return Subscale(
        name="subscale type item",
        scoring=SubscaleCalculationType.AVERAGE,
        items=[subscale_item],
    )


@pytest.fixture
def subscale_score_type() -> Subscale:
    return Subscale(
        name="subscale type score",
        scoring=SubscaleCalculationType.AVERAGE,
        items=[SubscaleItem(name="subscale_item", type=SubscaleItemType.ITEM)],
    )


@pytest.fixture
def scores_and_reports_lookup_scores(
    score_with_subcale: Score, section: Section, subscale: Subscale
) -> ScoresAndReports:
    return ScoresAndReports(
        generate_report=True,
        show_score_summary=True,
        reports=[score_with_subcale],
    )


@pytest.fixture
def subscale_item_type_subscale(subscale: Subscale) -> SubscaleItem:
    # Depends on subscalke because name should contain subscale item
    return SubscaleItem(name=subscale.name, type=SubscaleItemType.SUBSCALE)


@pytest.fixture
def subscale_with_item_type_subscale(subscale_item_type_subscale: SubscaleItem) -> Subscale:
    return Subscale(
        name="subscale type subscale",
        scoring=SubscaleCalculationType.AVERAGE,
        items=[subscale_item_type_subscale],
    )


@pytest.fixture
def subscale_setting(subscale: Subscale) -> SubscaleSetting:
    return SubscaleSetting(
        calculate_total_score=SubscaleCalculationType.AVERAGE,
        subscales=[subscale],
    )


@pytest.fixture
def subscale_setting_score_type(subscale_score_type: Subscale) -> SubscaleSetting:
    return SubscaleSetting(
        calculate_total_score=SubscaleCalculationType.AVERAGE,
        subscales=[subscale_score_type],
    )


@pytest.fixture
def subscale_total_score_table() -> list[TotalScoreTable]:
    return [
        TotalScoreTable(raw_score="0 ~ 2", optional_text="some url"),
        TotalScoreTable(raw_score="4 ~ 20", optional_text="some url"),
    ]


@pytest.fixture
def subscale_lookup_table() -> list[SubScaleLookupTable]:
    return [
        SubScaleLookupTable(score="10", age="10", sex="M", raw_score="1", optional_text="some url", severity="Minimal"),
        SubScaleLookupTable(score="20", age="10", sex="F", raw_score="2", optional_text="some url", severity="Mild"),
        SubScaleLookupTable(score="20", age=15, sex="F", raw_score="2", optional_text="some url", severity="Mild"),
        SubScaleLookupTable(score="20", sex="F", raw_score="2", optional_text="some url", severity="Mild"),
        SubScaleLookupTable(score="20", age="10~15", sex="F", raw_score="2", optional_text="some url", severity="Mild"),
        SubScaleLookupTable(score="20", age="0~5", sex="F", raw_score="2", optional_text="some url", severity="Mild"),
    ]
