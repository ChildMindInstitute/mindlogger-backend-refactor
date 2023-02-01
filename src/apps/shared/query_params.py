from typing import Any

from fastapi import Depends
from pydantic import BaseModel, Field


class BaseQueryParams(BaseModel):
    """
    Class to declare query parameters
    """

    search: str | None = None
    page: int = Field(gt=0, default=10)
    limit: int = Field(gt=0, default=10)
    ordering: str | None = None


class QueryParams(BaseModel):
    """
    Class to group query parameters into single format
    """

    filters: dict[str, Any] = Field(default_factory=dict)
    search: str | None = None
    page: int = Field(gt=0, default=10)
    limit: int = Field(gt=0, default=10)
    ordering: list[str] = Field(default_factory=list)


def parse_query_params(query_param_class):
    """
    Parses query parameters and group them into QueryParams
    """

    def _parse(query_params: query_param_class = Depends()):
        params: QueryParams = query_params
        grouped_query_params = QueryParams()
        for key, val in params.dict().items():
            if not val:
                continue
            if key == "search":
                grouped_query_params.search = val
            elif key == "page":
                grouped_query_params.page = val
            elif key == "limit":
                grouped_query_params.limit = val
            elif key == "ordering":
                grouped_query_params.ordering = val.split(",")
            else:
                grouped_query_params.filters[key] = val

        return grouped_query_params

    return _parse
