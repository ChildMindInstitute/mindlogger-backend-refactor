import asyncio
import enum
from typing import (
    Optional,
    Callable,
)

from pyld import (
    ContextResolver,
    jsonld,
)

from apps.jsonld_converter.errors import (
    JsonLDLoaderError,
    JsonLDProcessingError,
)


class LdKeyword(str, enum.Enum):
    context = '@context'
    type = '@type'
    id = "@id"
    value = "@value"
    graph = "@graph"
    language = "@language"
    list = "@list"


class ContextResolverAwareMixin:
    document_loader: Optional[Callable] = None
    context_resolver: ContextResolver = None

    async def load_remote_doc(self, remote_doc: str) -> dict:
        assert self.document_loader is not None
        try:
            return await asyncio.to_thread(self.document_loader, remote_doc)
        except Exception as e:
            raise JsonLDLoaderError(remote_doc) from e

    async def _expand(self, doc: dict | str, base_url: str | None = None):
        options = dict(
            base=base_url,
            contextResolver=self.context_resolver,
            documentLoader=self.document_loader,
        )
        try:
            return await asyncio.to_thread(jsonld.expand, doc, options)
        except Exception as e:
            raise JsonLDProcessingError(None, doc) from e
