import asyncio
from copy import deepcopy
from typing import Type

from apps.jsonld_converter.domain import LdAppletCreate
from apps.jsonld_converter.errors import JsonLDNotSupportedError
from apps.jsonld_converter.service.document import ReproActivity
from apps.jsonld_converter.service.document.base import (
    LdDocumentBase,
    ContainsNestedMixin,
    CommonFieldsMixin,
    LdKeyword,
)


class ReproProtocol(LdDocumentBase, ContainsNestedMixin, CommonFieldsMixin):

    ld_version: str | None = None
    ld_schema_version: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_description: dict[str, str] | None = None
    ld_about: dict[str, str] | None = None
    ld_image: str | None = None
    ld_shuffle: bool | None = None
    ld_allow: list[str] | None = None
    ld_watermark: str | None = None

    extra: dict | None = None
    properties: dict
    nested_by_order: list[LdDocumentBase] | None = None

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:Protocol',
            *cls.attr_processor.resolve_key('reproschema:Protocol')
        ]
        return cls.attr_processor.first(doc.get(LdKeyword.type)) in ld_types

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproActivity]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_description = self._get_ld_description(processed_doc, drop=True)
        self.ld_about = self._get_ld_about(processed_doc, drop=True)
        self.ld_shuffle = self._get_ld_shuffle(processed_doc, drop=True)
        self.ld_allow = self._get_ld_allow(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_watermark = self._get_ld_watermark(processed_doc, drop=True)

        self.properties = self._get_ld_properties_formatted(processed_doc)
        self.nested_by_order = await self._get_nested_items(processed_doc)

        self._load_extra(processed_doc)

    def _get_ld_watermark(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_single(doc, 'schema:watermark', ld_key=LdKeyword.id, drop=drop)

    def _get_ld_shuffle(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'reproschema:shuffle', drop=drop)

    def _get_ld_allow(self, doc: dict, drop=False):
        key = self.attr_processor.get_key(doc, 'reproschema:allow')
        items = doc[key]
        if isinstance(items, list):
            return [item.get(LdKeyword.id) for item in items]
        if drop:
            del doc[key]

    async def _get_nested_items(self, doc: dict, drop=False):
        if items := self.attr_processor.get_attr_list(doc, 'reproschema:order', drop=drop):
            nested = await asyncio.gather(*[self._load_nested_doc(item) for item in items])
            return [node for node in nested if node]

    async def _load_nested_doc(self, doc: dict):
        try:
            node = await self.load_supported_document(doc, self.base_url)
            # override from properties
            if node.ld_id in self.properties:
                for prop, val in self.properties[node.ld_id].items():
                    if val is not None and hasattr(node, prop):
                        setattr(node, prop, val)
            return node
        except JsonLDNotSupportedError:
            return None  # TODO

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self):
        activities = [nested.export() for nested in self.nested_by_order if isinstance(nested, ReproActivity)]
        activity_flows = []
        return LdAppletCreate(
            display_name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            about=self.ld_about or {},
            image=self.ld_image or '',
            watermark=self.ld_watermark or '',
            activities=activities,
            activity_flows=activity_flows,
            extra_fields=self.extra,
        )
