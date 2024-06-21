import pytest

from apps.activities.domain import conditions as cnd
from apps.activities.domain.conditional_logic import ConditionalLogic, Match
from apps.activities.tests.utils import DEFAULT_ITEM_NAME


@pytest.fixture
def condition_equal() -> cnd.EqualCondition:
    return cnd.EqualCondition(
        item_name=DEFAULT_ITEM_NAME,
        type=cnd.ConditionType.EQUAL,
        payload=cnd.ValuePayload(value=1),
    )


@pytest.fixture
def condition_between() -> cnd.BetweenCondition:
    return cnd.BetweenCondition(
        item_name=DEFAULT_ITEM_NAME, type=cnd.ConditionType.BETWEEN, payload=cnd.MinMaxPayload(min_value=0, max_value=2)
    )


@pytest.fixture
def condition_rows_outside_of() -> cnd.OutsideOfCondition:
    return cnd.OutsideOfCondition(
        item_name=DEFAULT_ITEM_NAME, payload=cnd.MinMaxPayload(min_value=0, max_value=10, row_index=0)
    )


@pytest.fixture
def conditional_logic_equal(condition_equal: cnd.EqualCondition) -> ConditionalLogic:
    return ConditionalLogic(match=Match.ALL, conditions=[condition_equal])


@pytest.fixture
def conditional_logic_between(condition_between: cnd.BetweenCondition) -> ConditionalLogic:
    return ConditionalLogic(math=Match.ALL, conditions=[condition_between])


@pytest.fixture
def conditional_logic_rows_outside_of(condition_rows_outside_of: cnd.OutsideOfCondition) -> ConditionalLogic:
    return ConditionalLogic(math=Match.ALL, conditions=[condition_rows_outside_of])
