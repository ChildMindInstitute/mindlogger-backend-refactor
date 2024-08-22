import dataclasses
import re
from abc import ABC, abstractmethod
from operator import and_, or_
from typing import Tuple

from pydantic import parse_obj_as

from apps.activities.domain.conditional_logic import Match
from apps.activities.domain.conditions import AnyCondition, ConditionType
from apps.jsonld_converter.errors import ConditionalLogicError, ConditionalLogicParsingError


@dataclasses.dataclass
class ConditionData:
    var_name: str
    type: ConditionType
    values: list


class ConditionalLogicParser:
    """
    Parse expressions like:
        "condition1 || condition2 || ..."
        "condition1 && condition2 && ..."
    supported conditions:
        "{variable} == {int}"
        "{variable} === {int}"
        "{variable} != {int}"
        "{variable} !== {int}"
        "{variable} > {int}"
        "{variable} >= {int}"
        "{variable} < {int}"
        "{variable} <= {int}"
        "({variable} > {int1} && {variable} < {int2})"
        "({variable} >= {int1} && {variable} <= {int2})"
        "({variable} < {int1} || {variable} > {int2})"
        "({variable} <= {int1} || {variable} >= {int2})"
        "{variable}.includes({int})"
        "!{variable}.includes({int})"
        E.g. "input_radio == 0 || input_checkbox.includes(0)
            || (input_slider > 1 && input_slider < 3) || input_slider > 1
            || input_slider < 2|| input_slider != 4
            || (input_slider < 4 || input_slider > 5)
            || !input_checkbox.includes(1)"
    """

    re_var = r"[0-9a-zA-Z][\w_\-]*"

    #  "({variable} >= {int1} && {variable} <= {int2})"
    #  "({variable} <= {int1} || {variable} >= {int2})"
    re_range = rf"\(\s*({re_var})\s*(<|>)\s*([\d]+)\s*(\|\||&&)\s*({re_var})\s*(>|<)\s*([\d]+)\s*\)"  # noqa

    #  "{variable}.includes({int})"
    #  "!{variable}.includes({int})"
    re_includes = rf"(!?{re_var})\.(includes)\(([\d]+)\)"

    #  "{variable} <= {int}"
    re_comparison = rf"({re_var})\s*(\=\=\=?|>\=?|<\=?|!\=\=?)\s*(\d+)"

    #  "{variable} == {bool}"
    re_bool = rf"({re_var})\s*\=\=\=?\s*(true|false)"

    re_operator = rf"(?:{re_includes}|{re_comparison}|{re_bool})"

    marker_processed = "PROCESSED"

    def __init__(self, expression: str):
        self.expression: str = expression
        self.parts: list[ConditionData] = []

    def _process_range(self, match_obj):
        var_left, op_left = match_obj.group(1), match_obj.group(2)
        val_left, val_right = match_obj.group(3), match_obj.group(7)
        var_right, op_right = match_obj.group(5), match_obj.group(6)
        bool_op = match_obj.group(4)
        valid = and_(
            var_left == var_right,
            or_(
                # in range
                op_left in "<=" and op_right in ">=" and bool_op == "||",
                # out of range
                op_left in ">=" and op_right in "<=" and bool_op == "&&",
            ),
        )

        if not valid:
            raise ConditionalLogicParsingError("Cannot process condition logic")

        operator = ConditionType.BETWEEN if bool_op == "&&" else ConditionType.OUTSIDE_OF
        self.parts.append(ConditionData(var_left, operator, [val_left, val_right]))
        return self.marker_processed

    def _process_operator(self, match_obj):
        var: str | None = None  # type: ignore[annotation-unchecked]
        operator: str | None = None  # type: ignore[annotation-unchecked]
        value: str | bool | None = None  # type: ignore[annotation-unchecked]
        if match_obj.group(1) is not None:
            var = match_obj.group(1)
            operator = match_obj.group(2)
            value = match_obj.group(3)
            if var.startswith("!"):
                var = var[1:]
                operator = f"!{operator}"
        elif match_obj.group(4) is not None:
            var = match_obj.group(4)
            operator = match_obj.group(5)
            value = match_obj.group(6)
            if operator == "===" or operator == "!==":
                operator = operator[:-1]
        elif match_obj.group(7) is not None:
            var = match_obj.group(7)
            value = match_obj.group(8)
            value = True if value == "true" else False
            operator = "=="

        if var:
            self.parts.append(ConditionData(var, self._resolve_operator_value(operator), [value]))
            return self.marker_processed

        raise ConditionalLogicParsingError("Cannot process condition logic")

    def _resolve_operator_value(self, val: str):
        value_map = {
            "==": ConditionType.EQUAL,
            "!=": ConditionType.NOT_EQUAL,
            ">": ConditionType.GREATER_THAN,
            ">=": ConditionType.GREATER_THAN,  # TODO include bounds
            "<": ConditionType.LESS_THAN,
            "<=": ConditionType.LESS_THAN,  # TODO include bounds
            "includes": ConditionType.INCLUDES_OPTION,
            "!includes": ConditionType.NOT_INCLUDES_OPTION,
        }

        return value_map[val]

    def parse(self) -> Tuple[Match, list[ConditionData]]:
        """
        Parse expression of condition logic
        @return: (operator, parsed conditions)
        """

        self.parts = []
        processors = [
            (self.re_range, self._process_range),
            (self.re_operator, self._process_operator),
        ]
        subj = self.expression
        try:
            for pattern, processor in processors:
                subj = re.sub(pattern, processor, subj)
        except ConditionalLogicParsingError as e:
            raise ConditionalLogicError(self.expression) from e

        operator = "&&"
        is_operator_and = "&&" in subj
        is_operator_or = "||" in subj
        if is_operator_and and is_operator_or:
            raise ConditionalLogicError(self.expression)
        if is_operator_or:
            operator = "||"

        conditions = subj.replace(" ", "").split(operator)
        if len(set(conditions)) > 1:
            raise ConditionalLogicError(self.expression)

        match = Match.ALL if operator == "&&" else Match.ANY
        return match, self.parts


class ConditionResolver(ABC):
    @classmethod
    @abstractmethod
    def resolve(cls, name: str, condition: ConditionData) -> AnyCondition: ...


class ConditionValueResolver:
    @classmethod
    def resolve(cls, name: str, condition: ConditionData) -> AnyCondition:
        payload = None
        if condition.type in [
            ConditionType.EQUAL,
            ConditionType.NOT_EQUAL,
            ConditionType.LESS_THAN,
            ConditionType.GREATER_THAN,
        ]:
            payload = dict(value=int(condition.values[0]))
        elif condition.type in [
            ConditionType.BETWEEN,
            ConditionType.OUTSIDE_OF,
        ]:
            payload = dict(
                min_value=int(condition.values[0]),
                max_value=int(condition.values[1]),
            )

        if not payload:
            raise NotImplementedError(f'Condition type "{condition.type}" not supported')

        data = dict(item_name=name, type=condition.type, payload=payload)

        return parse_obj_as(AnyCondition, data)  # type: ignore[arg-type]


class ConditionBoolResolver:
    @classmethod
    def resolve(cls, name: str, condition: ConditionData) -> AnyCondition:
        val = condition.values[0]
        if condition.type != ConditionType.EQUAL or not isinstance(val, bool):
            raise NotImplementedError(f'Condition type "{condition.type}" not supported')

        data = dict(
            item_name=name,
            type=ConditionType.EQUAL_TO_SCORE,
            payload=dict(value=val),
        )

        return parse_obj_as(AnyCondition, data)  # type: ignore[arg-type]


class ConditionOptionResolver:
    @classmethod
    def resolve(cls, name: str, condition: ConditionData) -> AnyCondition:
        if condition.type in (
            ConditionType.INCLUDES_OPTION,
            ConditionType.NOT_INCLUDES_OPTION,
        ):
            _type = condition.type
        elif condition.type == ConditionType.EQUAL:
            _type = ConditionType.EQUAL_TO_OPTION
        elif condition.type == ConditionType.NOT_EQUAL:
            _type = ConditionType.NOT_EQUAL_TO_OPTION
        else:
            raise NotImplementedError(f'Condition type "{condition.type}" not supported')

        data = dict(
            item_name=name,
            type=_type,
            payload=dict(option_value=condition.values[0]),
        )
        return parse_obj_as(AnyCondition, data)  # type: ignore[arg-type]


class ResolvesConditionalLogic(ABC):
    ld_variable_name: str | None = None

    @abstractmethod
    def resolve_condition_name(self): ...

    @abstractmethod
    def resolve_condition(self, condition: ConditionData) -> AnyCondition: ...
