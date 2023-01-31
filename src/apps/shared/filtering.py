import operator

__all__ = ["Filtering", "FilterField"]

from sqlalchemy import Column

lookups = {
    "eq": operator.eq,
    "neq": operator.ne,
}


class FilterField(object):
    def __init__(self, field: Column, lookup: str = "eq"):
        assert lookup is not None and isinstance(lookup, str)
        self.field = field
        self.lookup = lookup
        self._lookup = lookups.get(lookup, lookups["eq"])

    def generate_filter(self, val):
        return self._lookup(self.field, val)


class Filtering(object):
    def __init__(self):
        self.fields = dict()
        for name, filter_field in self.__class__.__dict__.items():
            if isinstance(filter_field, FilterField):
                self.fields[name] = filter_field

    def get_clauses(self, **kwargs):
        clauses = []
        for name, value in kwargs.items():
            filter_field = self.fields.get(name)
            if not filter_field:
                continue
            clauses.append(filter_field.generate_filter(value))
        return clauses
