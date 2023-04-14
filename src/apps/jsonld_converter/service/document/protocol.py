import asyncio
from copy import deepcopy
from typing import Type

from apps.applets.domain.applet_create_update import AppletCreate
from apps.jsonld_converter.errors import JsonLDNotSupportedError
from apps.jsonld_converter.service.document import ReproActivity
from apps.jsonld_converter.service.document.activity_flow import ReproActivityFlow
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
    ld_watermark: str | None = None

    extra: dict | None = None
    properties: dict
    nested_by_order: list[LdDocumentBase] | None = None
    flows_by_order: list[LdDocumentBase] | None = None

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:Protocol',
            'reproschema:ActivitySet',
            *cls.attr_processor.resolve_key('reproschema:Protocol'),
            *cls.attr_processor.resolve_key('reproschema:ActivitySet'),
        ]
        return cls.attr_processor.first(doc.get(LdKeyword.type)) in ld_types

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproActivity, ReproActivityFlow]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_description = self._get_ld_description(processed_doc, drop=True)
        self.ld_about = self._get_ld_about(processed_doc)  # TODO
        self.ld_shuffle = self._get_ld_shuffle(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_watermark = self._get_ld_watermark(processed_doc, drop=True)

        properties = self._get_ld_properties_formatted(processed_doc)
        flow_properties = self._get_ld_properties_formatted(processed_doc, key='reproschema:activityFlowProperties')
        self.properties = {**properties, **flow_properties}

        self.nested_by_order = await self._get_nested_items(processed_doc)
        self.flows_by_order = await self._get_nested_items(processed_doc, attr_container='reproschema:activityFlowOrder')

        self._load_extra(processed_doc)

    def _get_ld_watermark(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_single(doc, 'schema:watermark', ld_key=LdKeyword.id, drop=drop)

    def _get_ld_shuffle(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'reproschema:shuffle', drop=drop)

    def _get_ld_about(self, doc: dict, drop=False):
        about = super()._get_ld_about(doc, drop=drop)
        if not about:
            landing_page_content = self.attr_processor.get_translations(doc, 'reproschema:landingPageContent', drop=drop)
            if landing_page_content:
                landing_page_type = self.attr_processor.get_attr_value(doc, 'reproschema:landingPageType', drop=drop)
                if landing_page_type == 'image':
                    return {lang: self._wrap_wysiwyg_img(url) for lang, url in landing_page_content.items() if url}
                return landing_page_content

        return about

    async def _get_nested_items(self, doc: dict, drop=False, attr_container='reproschema:order') -> list:
        if items := self.attr_processor.get_attr_list(doc, attr_container, drop=drop):
            nested = await asyncio.gather(*[self._load_nested_doc(item) for item in items])
            return [node for node in nested if node]
        return []

    async def _load_nested_doc(self, doc: dict):
        try:
            node = await self.load_supported_document(doc, self.base_url, self.settings)
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

    def export(self) -> AppletCreate:
        activity_keys = {}
        activities = []
        for nested in self.nested_by_order:
            if isinstance(nested, ReproActivity):
                activity = nested.export()
                activity_keys[nested.ld_id] = activity.key
                activities.append(activity)
        activity_flows = []
        for flow in self.flows_by_order:
            if isinstance(flow, ReproActivityFlow):
                flow.activity_keys = activity_keys
                activity_flows.append(flow.export())

        return AppletCreate(
            display_name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            about=self.ld_about or {},
            image=self.ld_image or '',
            watermark=self.ld_watermark or '',
            activities=activities,
            activity_flows=activity_flows,
            extra_fields=self.extra,
            password=self.settings['protocol_password']
        )
