from sqlalchemy.orm import Query


def paging(query: Query, page=1, limit=10) -> Query:
    query = query.limit(limit)
    query = query.offset((page - 1) * limit)
    return query
