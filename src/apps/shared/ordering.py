from sqlalchemy import asc, desc

__all__ = ["Ordering"]

from sqlalchemy.orm import InstrumentedAttribute


class Ordering(object):
    actions = {
        "+": asc,
        "-": desc,
    }

    def __init__(self):
        self.fields = dict()
        for key, val in self.__class__.__dict__.items():
            if isinstance(val, InstrumentedAttribute):
                self.fields[key] = val

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

        if field not in self.fields:
            return None

        return self.actions[sign](self.fields[field])
