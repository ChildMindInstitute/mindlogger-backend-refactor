import pytest

from infrastructure.utility.opensearch_client import OpenSearchClient, OpenSearchClientTest

INDEX = "audit-logs"


@pytest.fixture
def fresh_client():
    OpenSearchClientTest._storage = {}
    OpenSearchClientTest._indices = set()
    OpenSearchClient._initialized = False
    OpenSearchClient._instance = None
    return OpenSearchClient()


@pytest.mark.asyncio
async def test_search_returns_indexed_documents(fresh_client: OpenSearchClient):
    await fresh_client.ensure_index(INDEX, {})
    await fresh_client.index_document(INDEX, {"event.id": "a"})
    await fresh_client.index_document(INDEX, {"event.id": "b"})

    response = await fresh_client.search(INDEX, query={"match_all": {}})

    sources = [h["_source"] for h in response["hits"]["hits"]]
    assert sources == [{"event.id": "a"}, {"event.id": "b"}]


@pytest.mark.asyncio
async def test_search_records_query_body_for_assertion(fresh_client: OpenSearchClient):
    await fresh_client.ensure_index(INDEX, {})
    query = {"bool": {"filter": [{"term": {"curious.applet_id": "applet-1"}}]}}
    sort = [{"@timestamp": "asc"}, {"event.id": "asc"}]

    await fresh_client.search(INDEX, query=query, sort=sort, size=50)

    assert fresh_client._client.last_search_body == {  # type: ignore[union-attr]
        "query": query,
        "sort": sort,
        "size": 50,
    }


@pytest.mark.asyncio
async def test_iter_search_paginates_until_exhausted(fresh_client: OpenSearchClient):
    await fresh_client.ensure_index(INDEX, {})
    for i in range(7):
        await fresh_client.index_document(INDEX, {"event.id": str(i)})

    out = []
    async for doc in fresh_client.iter_search(
        INDEX,
        query={"match_all": {}},
        sort=[{"event.id": "asc"}],
        page_size=3,
    ):
        out.append(doc["event.id"])

    assert out == ["0", "1", "2", "3", "4", "5", "6"]


@pytest.mark.asyncio
async def test_iter_search_stops_when_no_hits(fresh_client: OpenSearchClient):
    await fresh_client.ensure_index(INDEX, {})

    out = [
        doc
        async for doc in fresh_client.iter_search(
            INDEX, query={"match_all": {}}, sort=[{"event.id": "asc"}], page_size=10
        )
    ]

    assert out == []
