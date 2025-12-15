import datetime
import uuid
from typing import Annotated

from fastapi import Query
from pydantic import Field

from apps.applets.domain import Role
from apps.shared.query_params import BaseQueryParams
from config import settings


class AppletQueryParams(BaseQueryParams):
    roles: str = ",".join(Role.as_list())
    ordering: str = "-createdAt"
    folder_id: uuid.UUID | None = None
    limit: int = 10000
    flat_list: bool = False


class AppletUsersQueryParams(BaseQueryParams):
    role: Role | None = None


class FlowItemHistoryExportQueryParams(BaseQueryParams):
    flow_ids: Annotated[list[uuid.UUID] | None, Field(Query(None))]
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: Annotated[int, Field(gt=0, le=settings.service.result_limit)] = settings.service.result_limit
