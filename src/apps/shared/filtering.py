import operator

__all__ = ["Filtering", "FilterField"]

from enum import StrEnum

from sqlalchemy import Column


class Comparisons(StrEnum):
    EQUAL = "eq"
    NOT_EQUAL = "neq"
    IN = "in"
    GREAT_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"


def generate_clause(condition):
    def handle(field, value):
        clause = getattr(field, condition, None)
        return clause(value)

    return handle


lookups = {
    Comparisons.EQUAL: operator.eq,
    Comparisons.NOT_EQUAL: operator.ne,
    Comparisons.IN: generate_clause("in_"),
    Comparisons.GREAT_OR_EQUAL: operator.ge,
    Comparisons.LESS_OR_EQUAL: operator.le,
}


class FilterField:
    """
    Adds filter field by lookup
    Example:
        name = FilterField(Schema.first_name, lookup='eq')
    """

    def __init__(
        self,
        field: Column,
        lookup: Comparisons = Comparisons.EQUAL,
        cast=lambda x: x,
        method_name=None,
    ):
        assert lookup not in [None, ""] and isinstance(lookup, str)
        self.field = field
        self.lookup = lookup
        self._lookup = lookups.get(lookup, lookups[Comparisons.EQUAL])
        self.method_name = method_name
        self.cast = cast

    def generate_filter(self, val, filtering_method):
        if filtering_method:
            return filtering_method(self.field, self.cast(val))
        return self._lookup(self.field, self.cast(val))


class Filtering:
    """
    Generates filter clauses for query by
    provided filtering fields and conditions
    Example:
        class SchemaFilter(Filtering):
            name = FilterField(Schema.first_name, lookup='eq')

        SchemaFilter().get_clauses(name='Tom') will generate where clause like
        select * from schema where first_name='Tom'
    """

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
            filtering_method = None
            prepare_method = getattr(self, f"prepare_{name}", lambda x: x)
            if filter_field.method_name:
                filtering_method = getattr(self, filter_field.method_name, None)
            _clause = filter_field.generate_filter(prepare_method(value), filtering_method)
            if _clause is not None:
                clauses.append(_clause)
        return clauses

    def null(self, field, value):
        return field.is_(None) if value else field.isnot(None)
