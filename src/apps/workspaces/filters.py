import uuid

from apps.shared.query_params import BaseQueryParams, FilterNone
from apps.workspaces.domain.constants import Role


class WorkspaceUsersQueryParams(BaseQueryParams):
    role: Role | FilterNone = FilterNone()
    applet_id: uuid.UUID | FilterNone = FilterNone()
    ordering = "-pinned,-createdAt"
