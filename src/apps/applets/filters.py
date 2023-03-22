import uuid

from apps.applets.domain import Role
from apps.shared.query_params import BaseQueryParams


class AppletQueryParams(BaseQueryParams):
    roles: str = ",".join(Role.as_list())
    ordering: str = "-id"
    folder_id: str | None = None


class AppletUsersQueryParams(BaseQueryParams):
    role: Role | None = None
