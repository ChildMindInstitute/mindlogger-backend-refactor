import asyncio
import enum
import re
from typing import Callable, Optional

from pyld import ContextResolver, jsonld

from apps.jsonld_converter.errors import JsonLDLoaderError, JsonLDProcessingError


class LdKeyword(enum.StrEnum):
    context = "@context"
    type = "@type"
    id = "@id"
    value = "@value"
    graph = "@graph"
    language = "@language"
    list = "@list"
    version = "@version"


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
            raise JsonLDProcessingError("Document compacting error", doc) from e

    async def _compact(
        self,
        doc: dict | str,
        context: str | dict | list | None,
        base_url: str | None = None,
    ):
        options = dict(
            base=base_url,
            contextResolver=self.context_resolver,
            documentLoader=self.document_loader,
        )
        try:
            return await asyncio.to_thread(jsonld.compact, doc, context, options)
        except Exception as e:
            raise JsonLDProcessingError("Document expanding error", doc) from e


def str_to_id(name: str, to_underscore=r"\s") -> str:
    if name is None:
        return ""
    name = re.sub(r"[^0-9a-zA-Z\s_-]+", "", name)
    if to_underscore:
        name = re.sub(rf"[{to_underscore}]+", "_", name)
    return name
