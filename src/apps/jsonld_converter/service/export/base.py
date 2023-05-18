import re
from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Type,
    Callable,
)

from pyld import ContextResolver

from apps.jsonld_converter.service.base import ContextResolverAwareMixin
from apps.shared.domain import InternalModel


class ContainsNestedModelMixin(ABC, ContextResolverAwareMixin):
    @classmethod
    @abstractmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]:
        ...

    def get_supported_processor(self, model: InternalModel) -> "BaseModelExport":
        for candidate in self.get_supported_types():
            if candidate.supports(model):
                return candidate(self.context_resolver, self.document_loader)
        raise Exception("Model not supported")  # TODO raise specific error


class BaseModelExport(ABC, ContextResolverAwareMixin):
    context: str = "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json"
    schema_version: str = "1.1"

    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader = document_loader

    @classmethod
    @abstractmethod
    def supports(cls, model: InternalModel) -> bool:
        ...

    @abstractmethod
    async def export(self, model: InternalModel, expand: bool = False) -> dict:
        ...

    async def _post_process(self, doc: dict, expand: bool):
        if expand:
            expanded = await self._expand(doc)
            return expanded[0]
        return doc

    @classmethod
    def str_to_id(cls, name: str) -> str:
        name = re.sub(r"[^0-9a-zA-Z\s_-]+", "", name)
        name = re.sub(r"[\s_-]+", "_", name)

        return name
