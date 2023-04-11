from abc import abstractmethod
from copy import deepcopy

from apps.activity_flows.domain.flow_create import (
    FlowCreate,
    FlowItemCreate,
)
from apps.jsonld_converter.service.document.base import (
    LdDocumentBase,
    CommonFieldsMixin,
    LdKeyword,
)


class ReproActivityFlow(LdDocumentBase, CommonFieldsMixin):
    ld_name: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_description: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None

    ld_combine_reports: bool | None = None
    ld_show_badge: bool | None = None

    flow_items: list[str] = None
    extra: dict | None = None

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:ActivityFlow',
            *cls.attr_processor.resolve_key('reproschema:ActivityFlow')
        ]
        return cls.attr_processor.first(doc.get(LdKeyword.type)) in ld_types

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_name = self.attr_processor.get_translation(processed_doc, 'schema:name', lang=self.lang)
        self.ld_description = self._get_ld_description(processed_doc, drop=True)
        self.ld_is_vis = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isVis')

        self.ld_combine_reports = self.attr_processor.get_attr_value(processed_doc, 'reproschema:combineReports')
        self.ld_show_badge = self.attr_processor.get_attr_value(processed_doc, 'reproschema:showBadge')

        self.flow_items = self._get_flow_items(processed_doc, drop=True)

        self._load_extra(processed_doc)

    def _get_flow_items(self, doc: dict, *, drop=False):
        if items := self.attr_processor.get_attr_list(doc, 'reproschema:order', drop=drop):
            return [item.get(LdKeyword.id) for item in items]

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self) -> FlowCreate:
        flow_items = []
        for activity_id in self.flow_items:
            item = FlowItemCreate(
                activity_key=activity_id,  # TODO activity key
            )
            flow_items.append(item)

        flow = FlowCreate(
            name=self.ld_pref_label or self.ld_alt_label or self.ld_name,
            description=self.ld_description or {},
            is_single_report=bool(self.ld_combine_reports),
            hide_badge=self.ld_show_badge is False,
            items=flow_items,
            is_hidden=self.ld_is_vis is False,
        )
        return flow
