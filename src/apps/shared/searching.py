from functools import reduce

from sqlalchemy import Unicode, or_

__all__ = ["Searching"]


class Searching:
    """
    Generates clause for search using `ilike`
    Example:
        class SchemaSearch(Searching):
            search_fields = [Schema.first_name]

        SchemaSearch().get_clauses('To')
        will generate where clause like below:
        select * from schema where first_name::text ilike '%To%'


    """

    search_fields: list = []

    def get_clauses(self, search_term):
        clauses = []
        if not search_term or not self.search_fields:
            return None
        for search_field in self.search_fields:
            clauses.append(search_field.cast(Unicode()).ilike(f"%{search_term}%"))

        return reduce(or_, clauses)
