import pytest

from apps.activities.domain.conditional_logic import ConditionalLogic, Match
from apps.activities.domain.conditions import ConditionType, EqualCondition, ValuePayload
from apps.activities.tests.utils import DEFAULT_ITEM_NAME


@pytest.fixture
def condition_equal() -> EqualCondition:
    return EqualCondition(
        item_name=DEFAULT_ITEM_NAME,
        type=ConditionType.EQUAL,
        payload=ValuePayload(value=1),
    )


@pytest.fixture
def conditional_logic(condition_equal: EqualCondition) -> ConditionalLogic:
    return ConditionalLogic(match=Match.ALL, conditions=[condition_equal])
