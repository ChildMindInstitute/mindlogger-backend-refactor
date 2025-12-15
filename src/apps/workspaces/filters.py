import uuid

from apps.shared.query_params import BaseQueryParams
from apps.workspaces.domain.constants import Role


class WorkspaceUsersQueryParams(BaseQueryParams):
    role: Role | None = None
    shell: bool | None = None
    user_id: uuid.UUID | None = None
    respondent_secret_id: str | None = None
    include_soft_deleted_subjects: bool = False
    ordering: str = "-isPinned,-createdAt"
