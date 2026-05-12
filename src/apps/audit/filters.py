import datetime

from apps.shared.query_params import BaseQueryParams


class AuditExportFilters(BaseQueryParams):
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    limit: int = 10000
