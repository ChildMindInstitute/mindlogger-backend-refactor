import datetime

from apps.shared.query_params import BaseQueryParams


class AuditExportFilters(BaseQueryParams):
    from_date: datetime.datetime | None = None
    to_date: datetime.datetime | None = None
    limit: int = 10000
