from apps.shared.query_params import BaseQueryParams


class AppletActivityFilter(BaseQueryParams):
    has_submitted: bool | None
    has_score: bool | None
