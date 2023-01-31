from functools import reduce

from sqlalchemy import Unicode, or_

__all__ = ["Searching"]


class Searching(object):
    search_fields: list = list()

    def get_clauses(self, search_term):
        clauses = []
        if not search_term or not self.search_fields:
            return None
        for search_field in self.search_fields:
            clauses.append(
                search_field.cast(Unicode()).ilike(f"%{search_term}%")
            )
        return reduce(or_, clauses)
