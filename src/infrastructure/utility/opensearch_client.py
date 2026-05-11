import typing
from typing import AsyncIterator, Sequence

from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError

from config import settings

DEFAULT_PAGE_SIZE = 1000


class OpenSearchClientTest:
    """In-memory test double — accumulates indexed documents per index.

    ``search`` returns documents in insertion order without applying the
    query DSL. Tests that need to verify filtering should assert against
    the query body directly, or use the integration suite against a real
    OpenSearch instance.
    """

    _storage: dict[str, list[dict]] = {}
    _indices: set[str] = set()
    last_search_body: dict = {}

    async def ensure_index(self, index: str, mapping: dict) -> None:
        self._indices.add(index)
        self._storage.setdefault(index, [])

    async def index_document(self, index: str, document: dict, id: str | None = None) -> None:
        self._storage.setdefault(index, []).append(document)

    async def close(self) -> None:
        pass

    async def search(self, index: str, body: dict, size: int = DEFAULT_PAGE_SIZE) -> dict:
        OpenSearchClientTest.last_search_body = body
        docs = self._storage.get(index, [])
        # Cursor is the last hit's index in storage; resume from the next one.
        cursor = body.get("search_after")
        start = (cursor[0] + 1) if cursor else 0
        page = docs[start : start + size]
        return {
            "hits": {
                "total": {"value": len(docs)},
                "hits": [{"_source": d, "sort": [start + i]} for i, d in enumerate(page)],
            }
        }

class OpenSearchClient:
    """Singleton OpenSearch client"""

    _initialized: bool = False
    _instance = None
    _client: typing.Union[AsyncOpenSearch, OpenSearchClientTest, None] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._start()
        self._initialized = True

    def _start(self) -> None:
        if settings.env == "testing":
            self._client = OpenSearchClientTest()
            return
        self._client = AsyncOpenSearch(
            hosts=[{"host": settings.opensearch.host, "port": settings.opensearch.port}],
            http_auth=(settings.opensearch.user, settings.opensearch.password),
            use_ssl=settings.opensearch.use_ssl,
            verify_certs=settings.opensearch.verify_certs,
            ssl_show_warn=False,
        )

    async def ensure_index(self, index: str, mapping: dict) -> None:
        if isinstance(self._client, OpenSearchClientTest):
            await self._client.ensure_index(index, mapping)
            return
        assert self._client is not None
        try:
            exists = await self._client.indices.exists(index=index)
            if not exists:
                await self._client.indices.create(index=index, body=mapping)
        except RequestError as e:
            if getattr(e, "error", None) != "resource_already_exists_exception":
                raise

    async def index_document(self, index: str, document: dict, id: str | None = None) -> None:
        if isinstance(self._client, OpenSearchClientTest):
            await self._client.index_document(index, document)
            return
        assert self._client is not None
        await self._client.index(index=index, body=document, id=id)

    async def close(self) -> None:
        if isinstance(self._client, AsyncOpenSearch):
            await self._client.close()

    async def search(
        self,
        index: str,
        query: dict,
        sort: Sequence[dict] | None = None,
        size: int = DEFAULT_PAGE_SIZE,
        search_after: list | None = None,
    ) -> dict:
        body: dict = {"query": query, "size": size}
        if sort is not None:
            body["sort"] = list(sort)
        if search_after is not None:
            body["search_after"] = search_after

        if isinstance(self._client, OpenSearchClientTest):
            return await self._client.search(index, body, size=size)
        assert self._client is not None
        return await self._client.search(index=index, body=body)

    async def iter_search(
        self,
        index: str,
        query: dict,
        sort: Sequence[dict],
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> AsyncIterator[dict]:
        """Stream every hit matching ``query`` using ``search_after`` paging.

        ``sort`` must include a tiebreaker unique per document
        (e.g. ``event.id``) so the cursor advances on every page.
        """
        cursor: list | None = None
        while True:
            response = await self.search(
                index,
                query=query,
                sort=sort,
                size=page_size,
                search_after=cursor,
            )
            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                return
            for hit in hits:
                yield hit["_source"]
            if len(hits) < page_size:
                return
            cursor = hits[-1].get("sort")
            if cursor is None:
                return
