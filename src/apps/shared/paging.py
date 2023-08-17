from typing import List, Optional

from sqlalchemy.orm import Query

from config import settings


def paging(query: Query, page=1, limit=10) -> Query:
    if limit is None:
        limit = settings.service.result_limit
    else:
        limit = min(limit, settings.service.result_limit)
    if page is None:
        page = 1

    query = query.limit(limit)
    query = query.offset((page - 1) * limit)
    return query


def paging_list(items: Optional[List], page=1, limit=10) -> list:
    if not items:
        return []
    start = (page - 1) * limit
    end = start + limit
    return items[start:end]
