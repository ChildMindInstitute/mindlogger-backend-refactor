import uuid

from apps.shared.query_params import BaseQueryParams
from apps.workspaces.domain.constants import Role


class WorkspaceUsersQueryParams(BaseQueryParams):
    role: Role | None
    shell: bool | None
    user_id: uuid.UUID | None = None
    respondent_secret_id: str | None = None
    ordering = "-isPinned,-createdAt"
