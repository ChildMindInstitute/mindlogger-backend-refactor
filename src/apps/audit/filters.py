import datetime

from apps.shared.query_params import BaseQueryParams


class AuditExportFilters(BaseQueryParams):
    from_datetime: datetime.datetime | None = None
    to_datetime: datetime.datetime | None = None
    limit: int = 10000
