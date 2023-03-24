from apps.shared.query_params import BaseQueryParams


class InvitationQueryParams(BaseQueryParams):
    ordering: str = "-id"
