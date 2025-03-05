import datetime
import uuid

from apps.applets.domain import Role
from apps.shared.query_params import BaseQueryParams


class AppletQueryParams(BaseQueryParams):
    roles: str = ",".join(Role.as_list())
    ordering: str = "-createdAt"
    folder_id: uuid.UUID | None
    limit: int = 10000
    flat_list: bool = False


class AppletUsersQueryParams(BaseQueryParams):
    role: Role | None = None


class FlowItemHistoryExportQueryParams(BaseQueryParams):
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000
