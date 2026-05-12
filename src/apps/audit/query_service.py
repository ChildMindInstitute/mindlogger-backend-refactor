import datetime
import uuid

from apps.audit.domain import AuditEvent
from config import settings
from infrastructure.utility.opensearch_client import OpenSearchClient

SORT: list[dict] = [{"@timestamp": "asc"}, {"event.id": "asc"}]


def _utc_midnight(d: datetime.date) -> str:
    return datetime.datetime.combine(d, datetime.time.min, tzinfo=datetime.timezone.utc).isoformat()


class AuditQueryService:
    def __init__(self, client: OpenSearchClient | None = None) -> None:
        self._client = client or OpenSearchClient()
        self._index = settings.opensearch.audit_index

    async def search_applet_events(
        self,
        applet_id: uuid.UUID,
        *,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
    ) -> tuple[list[AuditEvent], int]:
        query = self._build_query(applet_id, from_date, to_date)
        events = [
            AuditEvent.model_validate(doc)
            async for doc in self._client.iter_search(self._index, query=query, sort=SORT)
        ]
        return events, len(events)

    @staticmethod
    def _build_query(
        applet_id: uuid.UUID,
        from_date: datetime.date | None,
        to_date: datetime.date | None,
    ) -> dict:
        filters: list[dict] = [{"term": {"curious.applet_id": str(applet_id)}}]

        timestamp_range: dict = {}
        if from_date is not None:
            timestamp_range["gte"] = _utc_midnight(from_date)
        if to_date is not None:
            # to_date is inclusive at day granularity; +1 day at UTC midnight is the exclusive upper bound.
            timestamp_range["lt"] = _utc_midnight(to_date + datetime.timedelta(days=1))
        if timestamp_range:
            filters.append({"range": {"@timestamp": timestamp_range}})

        return {"bool": {"filter": filters}}
