from sqlalchemy import Column, asc, desc

__all__ = ["Ordering"]

from sqlalchemy.orm import InstrumentedAttribute


class Ordering:
    """
    Generates clauses for ordering
    Example:
        class ExampleOrdering(Ordering):
            id = Schema.id
            name = Schema.first_name

        ExampleOrdering().get_clauses('-id', 'name')
        will give result as sql:
        select * from schema order by id desc, first_name asc
    """

    class Clause:
        """
        Wrapper for complex ordering
        """

        def __init__(self, clause):
            self.clause = clause

    actions = {
        "+": asc,
        "-": desc,
    }

    def __init__(self):
        self.fields = dict()
        for key, val in self.__class__.__dict__.items():
            _val = None
            if isinstance(val, (InstrumentedAttribute, Column)):
                _val = val
            elif isinstance(val, Ordering.Clause):
                _val = val.clause
            if _val is not None:
                self.fields[key] = _val

    def get_clauses(self, *args):
        sorting_fields = []
        for value in args:
            ordering_field = self._prepare_ordered_field(value)
            if ordering_field is not None:
                sorting_fields.append(ordering_field)
        return sorting_fields

    def _prepare_ordered_field(self, value: str):
        if not value:
            return None
        sign, field = value[0], value[1:]
        if sign != "-":
            field = value
            sign = "+"
        field = field.lstrip("+")

        if field not in self.fields:
            return None

        return self.actions[sign](self.fields[field])
