import typing

from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError

from config import settings


class OpenSearchClientTest:
    """In-memory test double — accumulates indexed documents per index."""

    _storage: dict[str, list[dict]] = {}
    _indices: set[str] = set()

    async def ensure_index(self, index: str, mapping: dict) -> None:
        self._indices.add(index)
        self._storage.setdefault(index, [])

    async def index_document(self, index: str, document: dict, id: str | None = None) -> None:
        self._storage.setdefault(index, []).append(document)

    async def close(self) -> None:
        pass

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
