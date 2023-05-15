import uuid

from apps.shared.query_params import BaseQueryParams, FilterNone
from apps.workspaces.domain.constants import Role


class InvitationQueryParams(BaseQueryParams):
    ordering: str = "-id"
    applet_id: uuid.UUID | FilterNone = FilterNone()
    invitor_id: uuid.UUID | FilterNone = FilterNone()
    role: Role | FilterNone = FilterNone()
