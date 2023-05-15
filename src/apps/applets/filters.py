import uuid

from apps.applets.domain import Role
from apps.shared.query_params import BaseQueryParams, FilterNone


class AppletQueryParams(BaseQueryParams):
    roles: str = ",".join(Role.as_list())
    ordering: str = "-createdAt"
    folder_id: uuid.UUID | FilterNone = FilterNone()


class AppletUsersQueryParams(BaseQueryParams):
    role: Role | None = None
