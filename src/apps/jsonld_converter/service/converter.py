from typing import Callable, Type

from pyld import ContextResolver  # type: ignore[import]

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
    ReproFieldTime,
)
from apps.jsonld_converter.service.document.base import (
    ContainsNestedMixin,
    LdDocumentBase,
)
from apps.shared.domain import InternalModel


class JsonLDModelConverter(ContainsNestedMixin):
    """
    Converters json-ld document to internal model

    :example:
        document_loader = requests_document_loader()  # sync loader
        _resolved_context_cache = LRUCache(maxsize=100)
        context_resolver = ContextResolver(_resolved_context_cache, document_loader)  # noqa
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
            ReproFieldTime,
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
