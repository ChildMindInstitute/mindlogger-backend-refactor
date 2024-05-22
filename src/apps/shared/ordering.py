from functools import cmp_to_key
from typing import Literal, cast

from sqlalchemy import Column, asc, desc

from .domain.base import to_camelcase

__all__ = ["Ordering"]

from sqlalchemy.orm import InstrumentedAttribute

OrderingDirection = Literal["+", "-"]
OrderingField = str | tuple[str, int]


class Ordering:
    """
    Generates clauses for SQL ordering and utilities for manual ordering & pagination, if needed.

    For SQL ordering, add supported fields directly as class attributes as schema columns or
    ordering clauses.

    For manual ordering (i.e. required by encrypted fields), add them to the manual_fields
    dictionary, with the key representing the requested ordering field, and the value representing
    the column name as returned in each result record.
        **Note:** Also include in this dictionary any fields that are also supported by SQL
        ordering so that multi-key ordering continues to be supported when ordering manually.

    Example:
        class ExampleOrdering(Ordering):
            id = Schema.id
            date = Schema.created_at

            # manual_fields is optional, only needed if one or more fields are encrypted
            manual_fields = {
                "email": "email_encrypted",     # encrypted scalar field
                "nicknames": ("nicknames", 0),  # encrypted array field, index 0
                "id": "id",
                "date": "created_at",
            }

        ordering = ExampleOrdering()
        query.order_by(*ordering.get_clauses('-id', 'date'))
        # will give result as SQL:
        # select * from schema order by id desc, created_at asc

        manual_fields = ordering.get_manual_fields("nicknames", "email", "-date")
        if manual_fields:
            # run SQL query without ORDER BY query
            # then manually sort the results using manual_sort utility:
            data = ordering.manual_sort(data, manual_fields)
            # manually sorts decrypted data by:
            #   nicknames[0] (asc), email_encrypted (asc), then created_at (desc)
            data = ordering.manual_paginate(data, 1, 10)
            # manually paginates data, returns slice of first 10 records
    """

    class Clause:
        """
        Wrapper for complex ordering
        """

        def __init__(self, clause):
            self.clause = clause

    sql_fields: dict[str, Column] = dict()
    manual_fields: dict[str, OrderingField] = dict()

    actions = {
        "+": asc,
        "-": desc,
    }

    def __init__(self):
        self.sql_fields = dict()
        for key, val in self.__class__.__dict__.items():
            _val = None
            if isinstance(val, (InstrumentedAttribute, Column)):
                _val = val
            elif isinstance(val, Ordering.Clause):
                _val = val.clause
            if _val is not None:
                self.sql_fields[key] = _val

    # Returns array of parsed ordering arguments if any of the fields require manual sorting
    # (defined is self.manual_fields, but not in self.fields), else returns None.
    def get_manual_fields(self, *args: str):
        has_manual_only_fields = False
        parsed_fields: list[tuple[OrderingDirection, OrderingField]] = []
        for value in args:
            parsed_field = self._parse_ordered_field(value)
            if parsed_field is None:
                continue
            direction, field = parsed_field
            if not self._is_manual_field(field):
                continue
            parsed_fields.append((direction, self.manual_fields[field]))
            # Flag if any of the fields cannot be sorted by SQL (i.e. manual only)
            if not self._is_sql_field(field):
                has_manual_only_fields = True
        return parsed_fields if has_manual_only_fields else None

    # Returns SQL clauses suitable for Query.order_by based on provided "+field"-style args
    def get_clauses(self, *args):
        clauses: list[str] = []
        for value in args:
            parsed_field = self._parse_ordered_field(value)
            if parsed_field is None:
                continue
            _direction, field = parsed_field
            if not self._is_sql_field(field):
                continue
            clause = self._prepare_sql_clause(parsed_field)
            if clause is not None:
                clauses.append(clause)
        return clauses

    # Returns list of fields that this Ordering class supports for sorting, based on whether
    # to use manual sorting or not. Returns field names in camelCase suitable for API output.
    def get_ordering_fields(self, use_manual_sorting: bool = False):
        use_manual_sorting = use_manual_sorting and bool(self.manual_fields)
        fields = (self.manual_fields if use_manual_sorting else self.sql_fields).keys()
        return list(to_camelcase(word) for word in fields)

    def _is_sql_field(self, field: str):
        return field in self.sql_fields

    def _is_manual_field(self, field: str):
        return field in self.manual_fields

    def _parse_ordered_field(self, value: str):
        if not value:
            return None
        direction, field = value[0], value[1:]
        if direction != "-":
            field = value
            direction = "+"
        field = field.lstrip("+")
        return (direction, field)

    def _prepare_sql_clause(self, value: tuple[OrderingDirection, str]):
        direction, field = value
        if not self._is_sql_field(field):
            return None

        return self.actions[direction](self.sql_fields[field])

    def manual_sort(self, data: list, fields: list[tuple[OrderingDirection, OrderingField]]):
        def comparer(left, right):
            for direction, field in fields:
                left_value = right_value = None
                # Extract array field value
                if isinstance(field, tuple):
                    field, index = field
                    left_value = left[field][index]
                    right_value = right[field][index]
                # Extract scalar field value
                else:
                    left_value = left[field]
                    right_value = right[field]

                # Protect against None values (None ranks lowest in SQL by default)
                if left_value is None and right_value is None:
                    continue
                elif left_value is None:
                    # Set left value to maximum possible value for the type
                    if isinstance(right_value, (int, float)):
                        left_value = float("inf")  # maximum number
                    elif isinstance(right_value, str):
                        left_value = chr(1114111)  # maximum string
                elif right_value is None:
                    # Set right value to maximum possible value for the type
                    if isinstance(left_value, (int, float)):
                        right_value = float("inf")  # maximum number
                    elif isinstance(left_value, str):
                        right_value = chr(1114111)  # maximum string

                result = 0
                # Need to do conditional type casting strictly to satisfy type checker
                if isinstance(left_value, (int, float)):
                    right_value = cast(float, right_value)
                    result = (left_value > right_value) - (left_value < right_value)
                elif isinstance(left_value, str):
                    right_value = cast(str, right_value)
                    result = (left_value > right_value) - (left_value < right_value)

                multiplier = -1 if direction == "-" else 1
                if result:
                    return multiplier * result
            return 0

        return sorted(data, key=cmp_to_key(comparer))

    def manual_paginate(self, data: list, page_number: int, page_size: int):
        return data[(page_number - 1) * page_size : page_number * page_size]
