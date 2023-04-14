from apps.activity_flows.domain.flow_full import FlowFull
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
)
from apps.shared.domain import InternalModel


class ActivityFlowExport(BaseModelExport):
    @classmethod
    def supports(cls, model: InternalModel) -> bool:
        return isinstance(model, FlowFull)

    async def export(self, model: FlowFull) -> dict:
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: f"_:{model.id}",
            LdKeyword.type: "reproschema:ActivityFlow",
            "skos:prefLabel": model.name,
            "skos:altLabel": model.name,
            "schema:name": model.name,
            "schema:description": model.description,
            "combineReports": model.is_single_report,
            "showBadge": not model.hide_badge,
            "ui": self._build_ui_prop(model),
        }

        expanded = await self._expand(doc)

        return expanded[0]

    def _build_ui_prop(self, model: FlowFull) -> dict:
        order = [f"_:{item.activity_id}" for item in model.items]
        return {
            "order": order,
        }
