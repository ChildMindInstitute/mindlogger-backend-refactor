from abc import ABC, abstractmethod
from typing import Callable, Type

from pyld import ContextResolver

from apps.jsonld_converter.service.base import ContextResolverAwareMixin, str_to_id
from apps.jsonld_converter.service.domain import ModelExportData
from apps.shared.domain import InternalModel


class ContainsNestedModelMixin(ABC, ContextResolverAwareMixin):
    @classmethod
    @abstractmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]: ...

    def get_supported_processor(self, model: InternalModel) -> "BaseModelExport":
        for candidate in self.get_supported_types():
            if candidate.supports(model):
                return candidate(self.context_resolver, self.document_loader)  # type: ignore[arg-type]  # noqa: E501
        raise Exception("Model not supported")  # TODO raise specific error


class BaseModelExport(ABC, ContextResolverAwareMixin):
    context: list = [
        "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json",  # noqa: E501
    ]
    schema_version: str = "1.1"

    def __init__(
        self,
        context_resolver: ContextResolver,
        document_loader: Callable,
    ):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader = document_loader

    def _build_id(self, source: str, prefix="_"):
        id_ = str_to_id(source)
        return f"{prefix}:{id_}" if prefix else id_

    @classmethod
    @abstractmethod
    def supports(cls, model: InternalModel) -> bool: ...

    @abstractmethod
    async def export(self, model: InternalModel, expand: bool = False) -> ModelExportData: ...

    async def _post_process(self, doc: dict, expand: bool):
        if expand:
            expanded = await self._expand(doc)
            return expanded[0]
        return doc
