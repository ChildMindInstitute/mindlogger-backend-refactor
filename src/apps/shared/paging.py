from typing import List, Optional

from sqlalchemy.orm import Query


def paging(query: Query, page=1, limit=10) -> Query:
    query = query.limit(limit)
    query = query.offset((page - 1) * limit)
    return query


def paging_list(items: Optional[List], page=1, limit=10) -> list:
    if not items:
        return []
    start = (page - 1) * limit
    end = start + limit
    return items[start:end]
