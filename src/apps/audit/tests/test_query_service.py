import datetime
import uuid

import pytest

from apps.audit.domain import AuditEvent
from apps.audit.query_service import AuditQueryService
from infrastructure.utility.opensearch_client import OpenSearchClient, OpenSearchClientTest

INDEX = "audit-logs"


@pytest.fixture
def fresh_service() -> AuditQueryService:
    OpenSearchClientTest._storage = {}
    OpenSearchClientTest._indices = set()
    OpenSearchClientTest.last_search_body = {}
    OpenSearchClient._initialized = False
    OpenSearchClient._instance = None
    return AuditQueryService()


def _seed_doc(**overrides: object) -> dict:
    base: dict = {
        "@timestamp": "2026-05-01T10:00:00+00:00",
        "event.id": str(uuid.uuid4()),
        "event.action": "applet:answer:view",
        "user.id": str(uuid.uuid4()),
        "curious.applet_id": [str(uuid.uuid4())],
    }
    base.update(overrides)
    return base


async def test_query_filters_by_applet_and_dates(fresh_service: AuditQueryService):
    applet_id = uuid.uuid4()

    from_dt = datetime.datetime(2026, 5, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)
    to_dt = datetime.datetime(2026, 5, 7, 18, 0, 0, tzinfo=datetime.timezone.utc)

    await fresh_service.search_applet_events(
        applet_id,
        from_datetime=from_dt,
        to_datetime=to_dt,
    )

    body = OpenSearchClientTest.last_search_body
    filters = body["query"]["bool"]["filter"]
    assert filters[0] == {"term": {"curious.applet_id": str(applet_id)}}
    assert filters[1] == {
        "range": {
            "@timestamp": {
                "gte": "2026-05-01T14:30:00+00:00",
                "lt": "2026-05-07T18:00:00+00:00",
            }
        }
    }
    assert body["sort"] == [{"@timestamp": "asc"}, {"event.id": "asc"}]


async def test_query_omits_range_when_dates_missing(fresh_service: AuditQueryService):
    await fresh_service.search_applet_events(uuid.uuid4())

    filters = OpenSearchClientTest.last_search_body["query"]["bool"]["filter"]
    assert len(filters) == 1
    assert "range" not in filters[0]


async def test_yields_audit_events_in_storage_order(fresh_service: AuditQueryService):
    applet_id = uuid.uuid4()
    seeded_ids = []
    for _ in range(3):
        doc = _seed_doc(**{"curious.applet_id": [str(applet_id)]})
        seeded_ids.append(doc["event.id"])
        await OpenSearchClient().index_document(INDEX, doc)

    out, total = await fresh_service.search_applet_events(applet_id)

    assert total == 3
    assert len(out) == 3
    assert all(isinstance(e, AuditEvent) for e in out)
    assert [str(e.event_id) for e in out] == seeded_ids
