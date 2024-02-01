from apps.shared.query_params import BaseQueryParams
from apps.workspaces.domain.constants import Role


class WorkspaceUsersQueryParams(BaseQueryParams):
    role: Role | None
    shell: bool | None
    ordering = "-isPinned,-createdAt"
