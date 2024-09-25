from abc import ABC, abstractmethod
from typing import Type

from apps.activities.domain.conditional_logic import ConditionalLogic, Match
from apps.activities.domain.conditions import Condition, ConditionType, MinMaxPayload, OptionPayload, ValuePayload

__all__ = ["export_conditional_logic"]


condition_processors: list[Type["BaseExpression"]] = []


def register_expression(cls: Type["BaseExpression"]):
    condition_processors.append(cls)
    return cls


def export_condition(condition: Condition):
    for processor in condition_processors:
        if processor.supports(condition):
            return processor(condition).export()

    raise NotImplementedError(f'Condition "{condition.type}" not supported')


def export_conditional_logic(logic: ConditionalLogic) -> str:
    operator = "||" if logic.match == Match.ANY else "&&"
    expressions = [export_condition(condition) for condition in logic.conditions]

    return f" {operator} ".join(expressions)


class BaseExpression(ABC):
    def __init__(self, condition: Condition):
        self.condition = condition

    @classmethod
    @abstractmethod
    def supports(cls, condition: Condition) -> bool:
        ...

    @abstractmethod
    def export(self) -> str:
        ...


@register_expression
class ExpressionSimple(BaseExpression):
    simple_operator_map = {
        ConditionType.EQUAL: "==",
        ConditionType.EQUAL_TO_OPTION: "==",
        ConditionType.NOT_EQUAL: "!=",
        ConditionType.NOT_EQUAL_TO_OPTION: "!=",
        ConditionType.GREATER_THAN: ">",
        ConditionType.LESS_THAN: "<",
    }

    @classmethod
    def supports(cls, condition: Condition) -> bool:
        return condition.type in cls.simple_operator_map

    def export(self) -> str:
        type_ = self.condition.type
        name = self.condition.item_name
        payload = self.condition.payload
        operator = self.simple_operator_map.get(type_)  # type: ignore[call-overload] # noqa: E501
        if isinstance(payload, OptionPayload):
            try:
                val: int | str = int(payload.option_value)  # TODO actualize on PR merge
            except ValueError:
                val = f'"{payload.option_value}"'  # TODO actualize on PR merge
        elif isinstance(payload, ValuePayload):
            val = payload.value
        else:
            raise NotImplementedError

        return " ".join([name, operator, str(val)])


@register_expression
class ExpressionIncludes(BaseExpression):
    @classmethod
    def supports(cls, condition: Condition) -> bool:
        return condition.type in [
            ConditionType.INCLUDES_OPTION,
            ConditionType.NOT_INCLUDES_OPTION,
        ]

    def export(self) -> str:
        type_ = self.condition.type
        name = self.condition.item_name
        payload = self.condition.payload
        assert isinstance(payload, OptionPayload)
        try:
            val: int | str = int(payload.option_value)  # TODO actualize on PR merge
        except ValueError:
            val = f'"{payload.option_value}"'  # TODO actualize on PR merge

        res = f"{name}.includes({val})"  # TODO process str
        if type_ == ConditionType.NOT_INCLUDES_OPTION:
            res = "!" + res

        return res


@register_expression
class ExpressionRange(BaseExpression):
    @classmethod
    def supports(cls, condition: Condition) -> bool:
        return condition.type in [
            ConditionType.BETWEEN,
            ConditionType.OUTSIDE_OF,
        ]

    def export(self) -> str:
        type_ = self.condition.type
        name = self.condition.item_name
        payload = self.condition.payload
        assert isinstance(payload, MinMaxPayload)

        l_val, r_val = payload.min_value, payload.max_value
        if type_ == ConditionType.BETWEEN:
            l_op, r_op, byn_op = ">", "<", "&&"
        else:
            l_op, r_op, byn_op = "<", ">", "||"

        return f"({name} {l_op} {l_val} {byn_op} {name} {r_op} {r_val})"
