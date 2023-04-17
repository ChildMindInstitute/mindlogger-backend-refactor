import datetime
import uuid

from apps.shared.query_params import BaseQueryParams


class AppletActivityFilter(BaseQueryParams):
    respondent_id: uuid.UUID
    created_date: datetime.date
