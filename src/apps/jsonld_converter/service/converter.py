import enum
import json
import re
import zipfile
from io import BytesIO
from typing import Callable, Type

from pyld import ContextResolver

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
    ReproFieldTime,
    ReproFieldTimeRange,
    ReproFieldVideo,
    ReproProtocol,
)
from apps.jsonld_converter.service.document.base import ContainsNestedMixin, LdDocumentBase
from apps.jsonld_converter.service.export import AppletExport
from apps.jsonld_converter.service.export.base import BaseModelExport, ContainsNestedModelMixin


class JsonLDModelConverter(ContainsNestedMixin):
    """
    Converters json-ld document to internal model

    :example:
        document_loader = requests_document_loader()  # sync loader
        _resolved_context_cache = LRUCache(maxsize=100)
        context_resolver = ContextResolver(
            _resolved_context_cache, document_loader
        )
        settings = {"protocol_password": "password value"}

        converter = JsonLDModelConverter(context_resolver, document_loader)
        protocol = await converter.convert(document_url)

        With dependencies:

        document_loader = get_document_loader()
        context_resolver = get_context_resolver(document_loader)

        converter = get_jsonld_model_converter(
            document_loader, context_resolver
        )
        protocol = await converter.convert(doc)
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

    async def convert(self, input_: str | dict, base_url: str | None = None):
        obj = await self.load_supported_document(input_, base_url, self.settings)

        return obj.export()


class ExportFormat(enum.StrEnum):
    zip = "zip"
    list = "list"


def replace_batch(doc: str, replacements: dict):
    replacements = {re.escape(k): v for k, v in replacements.items()}
    pattern = re.compile("|".join(replacements.keys()))
    return pattern.sub(lambda m: replacements[re.escape(m.group(0))], doc)


class ModelJsonLDConverter(ContainsNestedModelMixin):
    CONTEXT_TO_COMPACT = "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json"  # noqa: E501

    url_prefix = "https://raw.githubusercontent.com"
    activities_url = f"{url_prefix}/YOUR-PATH-TO-ACTIVITIES-FOLDER"
    flows_url = f"{url_prefix}/YOUR-PATH-TO-ACTIVITY_FLOWS-FOLDER"

    activities_prefix = "activities"
    flows_prefix = "flows"

    def __init__(
        self,
        context_resolver: ContextResolver,
        document_loader: Callable,
    ):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader: Callable = document_loader

    @classmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]:
        return [AppletExport]

    def _generate_new_id(
        self,
        prefixed_id: str,
        new_prefix: str | None = None,
        new_id: str | None = None,
    ) -> str:
        parts = prefixed_id.split(":", 1)
        try:
            id_ = parts[1]
        except IndexError:
            id_ = prefixed_id

        new_id = new_id or id_
        if new_prefix:
            new_id = f"{new_prefix}{new_id}"

        return new_id

    async def to_list(self, model, compact=False):
        exporter = self.get_supported_processor(model)
        protocol_data = await exporter.export(model)

        return protocol_data

    async def to_zip(self, model, compact=False) -> BytesIO:
        data = await self.to_list(model, compact)

        schema = data.schema

        files = []

        protocol_doc = json.dumps(schema, indent=4)
        protocol_id = "protocol"
        protocol_replacements = {
            data.id: protocol_id,
        }

        activity_dir = "activities"
        for activity_data in data.activities:
            activity_doc = json.dumps(activity_data.schema, indent=4)
            new_activity_id = self._generate_new_id(activity_data.id)
            activity_path = f"{activity_dir}/{new_activity_id}/{new_activity_id}"
            activity_replacements = {activity_data.id: new_activity_id}
            protocol_replacements[activity_data.id] = activity_path

            for item_data in activity_data.activity_items:
                item_doc = json.dumps(item_data.schema, indent=4)
                new_item_id = self._generate_new_id(item_data.id)
                item_path = f"{activity_dir}/{new_activity_id}/items/{new_item_id}"
                activity_replacements[item_data.id] = item_path

                item_doc = item_doc.replace(item_data.id, new_item_id)

                files.append((item_path, item_doc))

            activity_doc = replace_batch(activity_doc, activity_replacements)

            files.append((activity_path, activity_doc))

        protocol_doc = replace_batch(protocol_doc, protocol_replacements)

        files.append((protocol_id, protocol_doc))

        res = BytesIO()

        with zipfile.ZipFile(res, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_name, data in files:
                zip_file.writestr(file_name, bytes(data, "UTF-8"))

        return res
