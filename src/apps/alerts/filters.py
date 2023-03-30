from apps.shared.query_params import BaseQueryParams


class AlertConfigQueryParams(BaseQueryParams):
    ordering: str = "-id"


class AlertQueryParams(BaseQueryParams):
    ordering: str = "-id"
