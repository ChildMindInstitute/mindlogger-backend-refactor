from typing import Callable

from cachetools import LRUCache
from fastapi import Depends
from pyld import ContextResolver
from pyld.jsonld import requests_document_loader

from apps.jsonld_converter.service import JsonLDModelConverter
from config import settings


def get_document_loader() -> Callable:
    return requests_document_loader()


def get_context_resolver(
    document_loader: Callable = Depends(get_document_loader),
) -> ContextResolver:
    _resolved_context_cache = LRUCache(maxsize=100)
    return ContextResolver(_resolved_context_cache, document_loader)


def get_jsonld_model_converter(
    document_loader: Callable = Depends(get_document_loader),
    context_resolver: ContextResolver = Depends(get_context_resolver),
) -> JsonLDModelConverter:
    return JsonLDModelConverter(
        context_resolver, document_loader, settings.jsonld_converter.dict()
    )
