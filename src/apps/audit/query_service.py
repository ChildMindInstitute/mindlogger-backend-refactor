import datetime
import uuid

from apps.audit.domain import AuditEvent
from config import settings
from infrastructure.utility.opensearch_client import DEFAULT_PAGE_SIZE, OpenSearchClient

SORT: list[dict] = [{"@timestamp": "asc"}, {"event.id": "asc"}]


class AuditQueryService:
    def __init__(self, client: OpenSearchClient | None = None) -> None:
        self._client = client or OpenSearchClient()
        self._index = settings.opensearch.audit_index

    async def search_applet_events(
        self,
        applet_id: uuid.UUID,
        *,
        from_datetime: datetime.datetime | None = None,
        to_datetime: datetime.datetime | None = None,
        page: int = 1,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[AuditEvent], int]:
        query = self._build_query(applet_id, from_datetime, to_datetime)
        response = await self._client.search(
            self._index,
            query=query,
            sort=SORT,
            size=limit,
            from_=(page - 1) * limit,
        )
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        events = [AuditEvent.model_validate(hit["_source"]) for hit in hits.get("hits", [])]
        return events, total

    @staticmethod
    def _build_query(
        applet_id: uuid.UUID,
        from_datetime: datetime.datetime | None,
        to_datetime: datetime.datetime | None,
    ) -> dict:
        filters: list[dict] = [{"term": {"curious.applet_id": str(applet_id)}}]

        timestamp_range: dict = {}
        if from_datetime is not None:
            timestamp_range["gte"] = from_datetime.isoformat()
        if to_datetime is not None:
            timestamp_range["lt"] = to_datetime.isoformat()
        if timestamp_range:
            filters.append({"range": {"@timestamp": timestamp_range}})

        return {"bool": {"filter": filters}}
