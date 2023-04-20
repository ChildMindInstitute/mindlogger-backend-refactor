from typing import Callable, Type

from pyld import ContextResolver

from apps.jsonld_converter.service.base import ContextResolverAwareMixin
from apps.jsonld_converter.service.document import (
    ReproActivity,
    ReproFieldAge,
    ReproFieldAudio,
    ReproFieldAudioStimulus,
    ReproFieldDate,
    ReproFieldDrawing,
    ReproFieldGeolocation,
    ReproFieldMessage,
    ReproFieldPhoto,
    ReproFieldRadio,
    ReproFieldRadioStacked,
    ReproFieldSlider,
    ReproFieldSliderStacked,
    ReproFieldText,
    ReproFieldTimeRange,
    ReproFieldVideo,
    ReproProtocol,
)
from apps.jsonld_converter.service.document.base import (
    ContainsNestedMixin,
    LdDocumentBase,
)
from apps.jsonld_converter.service.export import AppletExport
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
    ContainsNestedModelMixin,
)
from apps.shared.domain import InternalModel


class JsonLDModelConverter(ContainsNestedMixin):
    """
    Converters json-ld document to internal model
    :example:
        document_loader = requests_document_loader()  # sync loader
        _resolved_context_cache = LRUCache(maxsize=100)
        context_resolver = ContextResolver(_resolved_context_cache, document_loader)
        settings = {"protocol_password": "password value"}
        converter = JsonLDModelConverter(context_resolver, document_loader)
        protocol = await converter.convert(document_url)
    """

    def __init__(
        self,
        context_resolver: ContextResolver,
        document_loader: Callable,
        settings: dict,
    ):
        """
        @type settings: dict
            - protocol_password: protocol default password
        """
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader: Callable = document_loader
        self.settings = settings

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [
            ReproProtocol,
            ReproActivity,
            ReproFieldText,
            ReproFieldRadio,
            ReproFieldSlider,
            ReproFieldSliderStacked,
            ReproFieldPhoto,
            ReproFieldVideo,
            ReproFieldAudio,
            ReproFieldDrawing,
            ReproFieldMessage,
            ReproFieldTimeRange,
            ReproFieldDate,
            ReproFieldGeolocation,
            ReproFieldAge,
            ReproFieldRadioStacked,
            ReproFieldAudioStimulus,
        ]

    async def convert(
        self, input_: str | dict, base_url: str | None = None
    ) -> InternalModel:
        obj = await self.load_supported_document(
            input_, base_url, self.settings
        )

        return obj.export()


class ModelJsonLDConverter(ContainsNestedModelMixin):

    CONTEXT_TO_COMPACT = "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json"

    @classmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]:
        return [AppletExport]

    def __init__(
        self, context_resolver: ContextResolver, document_loader: Callable
    ):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader: Callable = document_loader

    async def convert(self, model, compact=False) -> dict:
        exporter = self.get_supported_processor(model)
        doc = await exporter.export(model)

        if compact:
            return await self._compact(doc, self.CONTEXT_TO_COMPACT)

        return doc
