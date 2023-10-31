import asyncio
from copy import deepcopy
from typing import Type

from apps.applets.domain.applet_create_update import AppletCreate
from apps.jsonld_converter.service.document import (
    ABTrailsIpadActivity,
    ABTrailsMobileActivity,
    FlankerActivity,
    ReproActivity,
    StabilityTaskActivity,
)
from apps.jsonld_converter.service.document.activity_flow import (
    ReproActivityFlow,
)
from apps.jsonld_converter.service.document.base import (
    CommonFieldsMixin,
    ContainsNestedMixin,
    LdDocumentBase,
    LdKeyword,
)
from apps.jsonld_converter.service.domain import NotEncryptedApplet


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
    ld_retention_period: int | None = None
    ld_retention_type: str | None = None
    ld_stream_enabled: bool | None = None

    extra: dict | None = None
    properties: dict
    nested_by_order: list[LdDocumentBase] | None = None
    flows_by_order: list[LdDocumentBase] | None = None
    report_config: dict | None = None

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            "reproschema:Protocol",
            "reproschema:ActivitySet",
            *cls.attr_processor.resolve_key("reproschema:Protocol"),
            *cls.attr_processor.resolve_key("reproschema:ActivitySet"),
        ]
        return cls.attr_processor.first(doc.get(LdKeyword.type)) in ld_types

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [
            ReproActivity,
            ReproActivityFlow,
            ABTrailsIpadActivity,
            ABTrailsMobileActivity,
            StabilityTaskActivity,
            FlankerActivity,
        ]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_description = self._get_ld_description(
            processed_doc, drop=True
        )
        self.ld_about = self._get_ld_about(processed_doc, drop=True)  # TODO
        self.ld_shuffle = self._get_ld_shuffle(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc, drop=True)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc, drop=True)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_watermark = self._get_ld_watermark(processed_doc, drop=True)
        self.ld_stream_enabled = self.attr_processor.get_attr_value(
            processed_doc, "reproschema:streamEnabled", drop=True
        )

        self.report_config = self._get_report_configuration(
            processed_doc, drop=True
        )

        properties = self._get_ld_properties_formatted(
            processed_doc, drop=True
        )
        self._to_extra("properties", properties, "fields")
        flow_properties = self._get_ld_properties_formatted(
            processed_doc, key="reproschema:activityFlowProperties", drop=True
        )
        self.properties = {**properties, **flow_properties}

        self.nested_by_order = await self._get_nested_items(
            processed_doc, drop=True
        )
        self.flows_by_order = await self._get_nested_items(
            processed_doc,
            attr_container="reproschema:activityFlowOrder",
            drop=True,
        )

        self._load_extra(processed_doc)

        rs = doc.get("retentionSettings", {})
        if rs.get("enabled", False):
            self.ld_retention_period = rs.get("period")
            self.ld_retention_type = rs.get("retention")

    def _get_report_configuration(
        self, processed_doc: dict, *, drop=False
    ) -> dict:
        report_config = self.attr_processor.get_attr_list(
            processed_doc, "reproschema:reportConfigs", drop=drop
        )
        cfg = {}
        for obj in report_config or []:
            name = self.attr_processor.get_attr_value(obj, "schema:name")
            if name == "emailRecipients":
                ld_recipients = self.attr_processor.get_attr_list(
                    obj, "schema:value"
                )
                value = list(
                    {
                        recipient.get(LdKeyword.value)
                        for recipient in ld_recipients or []
                    }
                )
            elif name == "emailBody":  # TODO add translations to extra
                value = self.attr_processor.get_translation(
                    obj, "schema:value", self.lang
                )
            else:
                value = self.attr_processor.get_attr_value(obj, "schema:value")
            cfg[name] = value

        return cfg

    def _get_ld_watermark(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_single(
            doc, "schema:watermark", ld_key=LdKeyword.id, drop=drop
        )

    def _get_ld_shuffle(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(
            doc, "reproschema:shuffle", drop=drop
        )

    def _get_ld_about(self, doc: dict, drop=False):
        about = super()._get_ld_about(doc, drop=drop)
        if not about:
            landing_page_content = self.attr_processor.get_translations(
                doc, "reproschema:landingPageContent", drop=drop
            )
            if landing_page_content:
                landing_page_type = self.attr_processor.get_attr_value(
                    doc, "reproschema:landingPageType", drop=drop
                )
                if landing_page_type == "image":
                    return {
                        lang: self._wrap_wysiwyg_img(url)
                        for lang, url in landing_page_content.items()
                        if url
                    }
                return landing_page_content

        return about

    async def _get_nested_items(
        self, doc: dict, drop=False, attr_container="reproschema:order"
    ) -> list:
        nested_items = []
        if items := self.attr_processor.get_attr_list(
            doc, attr_container, drop=drop
        ):
            nested = await asyncio.gather(
                *[self._load_nested_doc(item) for item in items],
                return_exceptions=True,
            )
            for node in nested:
                if isinstance(node, Exception):
                    raise node
                if node:
                    nested_items.append(node)

        return nested_items

    async def _load_nested_doc(self, doc: dict):
        node = await self.load_supported_document(
            doc, self.base_url, self.settings
        )
        # override from properties
        if node.ld_id in self.properties:
            for prop, val in self.properties[node.ld_id].items():
                if val is not None and hasattr(node, prop):
                    setattr(node, prop, val)
        return node

    def export(self) -> AppletCreate:
        activity_keys = {}
        activities = []
        for nested in self.nested_by_order or []:
            if isinstance(nested, ReproActivity):
                assert nested.ld_id is not None

                activity = nested.export()
                activity_keys[nested.ld_id] = activity.key
                activities.append(activity)
        activity_flows = []
        for flow in self.flows_by_order or []:
            if isinstance(flow, ReproActivityFlow):
                flow.activity_keys = activity_keys
                activity_flows.append(flow.export())

        report_cfg = self.report_config or {}

        return NotEncryptedApplet(
            display_name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            about=self.ld_about or {},
            image=self.ld_image or "",
            watermark=self.ld_watermark or "",
            activities=activities,
            activity_flows=activity_flows,
            stream_enabled=self.ld_stream_enabled or False,
            extra_fields=self.extra,
            # encryption: Encryption  # TODO
            # theme_id: uuid.UUID | None = None
            # link: uuid.UUID | None
            # require_login: bool | None
            # pinned_at: datetime.datetime | None
            retention_period=self.ld_retention_period
            if self.ld_retention_period > 0
            else None,
            retention_type=self.ld_retention_type,
            report_server_ip=report_cfg.get("serverIp") or "",
            report_public_key=report_cfg.get("publicEncryptionKey") or "",
            report_recipients=report_cfg.get("emailRecipients") or [],
            report_include_user_id=report_cfg.get("includeUserId") or False,
            report_include_case_id=report_cfg.get("includeCaseId") or False,
            report_email_body=report_cfg.get("emailBody") or "",
        )
