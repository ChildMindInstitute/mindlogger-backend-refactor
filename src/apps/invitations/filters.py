import uuid

from apps.shared.query_params import BaseQueryParams
from apps.workspaces.domain.constants import Role


class InvitationQueryParams(BaseQueryParams):
    ordering: str = "-id"
    applet_id: uuid.UUID | None = None
    invitor_id: uuid.UUID | None = None
    role: Role | None = None
