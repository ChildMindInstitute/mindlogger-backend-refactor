import pytest

from apps.activities.domain.custom_validation_subscale import validate_raw_score_subscale, validate_score_subscale_table
from apps.activities.domain.response_type_config import ResponseType
from apps.activities.errors import InvalidRawScoreSubscaleError, InvalidScoreSubscaleError

ACTIVITY_ITEM_OPTIONS = [
    ResponseType.SINGLESELECT,
    ResponseType.MULTISELECT,
    ResponseType.SLIDER,
]


class TestValidateScoreSubscaleTable:
    def test_successful_validation(self):
        score = "1"
        assert score == validate_score_subscale_table(score)
        score = "1.2342~1231"
        assert score == validate_score_subscale_table(score)
        score = "1.2342~1231.12333"
        assert score == validate_score_subscale_table(score)

    def test_tilda_not_in_float_value_error(self):
        score = "1.1"
        with pytest.raises(InvalidScoreSubscaleError):
            validate_score_subscale_table(score)

    def test_not_float_value_error(self):
        score = "1.2342s~1231"
        with pytest.raises(InvalidScoreSubscaleError):
            validate_score_subscale_table(score)

    def test_too_long_fractional_part_error(self):
        score = "1.123456~1231"
        with pytest.raises(InvalidScoreSubscaleError):
            validate_score_subscale_table(score)


class TestValidateRawScoreSubscale:
    def test_successful_validation(self):
        raw_score = "1"
        assert raw_score == validate_raw_score_subscale(raw_score)
        raw_score = "12342~1231"
        assert raw_score == validate_raw_score_subscale(raw_score)

    def test_tilda_not_in_integer_value_error(self):
        raw_score = "1.1"
        with pytest.raises(InvalidRawScoreSubscaleError):
            validate_raw_score_subscale(raw_score)

    def test_not_integer_value_error(self):
        raw_score = "12342.1~1231"
        with pytest.raises(InvalidRawScoreSubscaleError):
            validate_raw_score_subscale(raw_score)
