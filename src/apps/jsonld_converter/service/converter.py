from typing import (
    Callable,
    Type,
)

from pyld import (
    ContextResolver,
)

from apps.jsonld_converter.service.reproschema_document import (
    ContainsNestedMixin,
    LdDocumentBase,
    ReproActivity,
    ReproProtocol,
)
from apps.shared.domain import InternalModel


class JsonLDModelConverter(ContainsNestedMixin):
    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader: Callable = document_loader

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproProtocol, ReproActivity]

    async def convert(self, input_: str | dict,
                      base_url: str | None = None) -> InternalModel:
        obj = await self.load_supported_document(input_, base_url)

        return obj.export()
