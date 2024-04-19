from typing import cast

import pytest

from apps.activities import errors
from apps.activities.domain.scores_reports import (
    Score,
    ScoreConditionalLogic,
    ScoresAndReports,
    Subscale,
    SubscaleSetting,
)


@pytest.mark.parametrize(
    "fixture_name, error",
    (
        ("score", errors.DuplicateScoreNameError),
        ("section", errors.DuplicateSectionNameError),
    ),
)
def test_duplicated_name_is_not_allowed(scores_and_reports: ScoresAndReports, request, fixture_name: str, error):
    model = request.getfixturevalue(fixture_name)
    copy = model.copy(deep=True)
    data = scores_and_reports.dict()
    data["reports"].append(copy.dict())
    with pytest.raises(error):
        ScoresAndReports(**data)


def test_duplicated_id_for_score_is_not_allowed(scores_and_reports: ScoresAndReports, score: Score):
    copy = score.copy(deep=True)
    # make name unique for test because we want to test the same ids not names
    copy.name = score.name + "1"
    data = scores_and_reports.dict()
    data["reports"].append(copy.dict())
    with pytest.raises(errors.DuplicateScoreIdError):
        ScoresAndReports(**data)


def test_score_and_reports_duplicated_name_in_conditional_logic_is_not_allowed_for_score(  # noqa: E501
    scores_and_reports: ScoresAndReports,
    score: Score,
    score_conditional_logic: ScoreConditionalLogic,
):
    copy = score_conditional_logic.copy(deep=True)
    copy.id = score_conditional_logic.id + "1"
    score_data = score.dict()
    score_data["conditional_logic"] = [
        score_conditional_logic.dict(),
        copy.dict(),
    ]
    data = scores_and_reports.dict()
    data["reports"] = [score_data]
    with pytest.raises(errors.DuplicateScoreConditionNameError):
        ScoresAndReports(**data)


def test_score_and_reports_duplicated_id_in_conditional_logic_is_not_allowed_for_score(  # noqa: E501
    scores_and_reports: ScoresAndReports,
    score: Score,
    score_conditional_logic: ScoreConditionalLogic,
):
    copy = score_conditional_logic.copy(deep=True)
    copy.name = score_conditional_logic.name + "1"
    score_data = score.dict()
    score_data["conditional_logic"] = [
        score_conditional_logic.dict(),
        copy.dict(),
    ]
    data = scores_and_reports.dict()
    data["reports"] = [score_data]
    with pytest.raises(errors.DuplicateScoreConditionIdError):
        ScoresAndReports(**data)


def test_duplicated_name_for_subscale_settings_is_not_allowed(subscale_setting: SubscaleSetting, subscale: Subscale):
    copy = subscale.copy(deep=True)
    subscale_setting.subscales = cast(list, subscale_setting.subscales)
    subscale_setting.subscales.append(copy)
    data = subscale_setting.dict()
    with pytest.raises(errors.DuplicateSubscaleNameError):
        SubscaleSetting(**data)


def test_score_duplicated_item_score_are_not_allowed(score: Score):
    data = score.dict()
    data["items_score"] = ["duplicate", "duplicate"]
    with pytest.raises(errors.DuplicateScoreItemNameError):
        Score(**data)


def test_score_conditional_logic_condition_item_name_is_not_the_same_with_score_id(  # noqa: E501
    score: Score,
    score_conditional_logic: ScoreConditionalLogic,
):
    data = score.dict()
    conditional_logic_data = score_conditional_logic.dict()
    conditional_logic_data["conditions"][0]["item_name"] = score.id + "1"
    data["conditional_logic"] = [conditional_logic_data]
    with pytest.raises(errors.ScoreConditionItemNameError):
        Score(**data)
