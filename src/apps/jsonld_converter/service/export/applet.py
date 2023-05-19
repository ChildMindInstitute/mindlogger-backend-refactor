import asyncio
from typing import Type

from apps.applets.domain.applet_full import AppletFull
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.export import (
    ActivityExport,
    ActivityFlowExport,
)
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
    ContainsNestedModelMixin,
)
from apps.shared.domain import InternalModel


class AppletExport(BaseModelExport, ContainsNestedModelMixin):
    @classmethod
    def supports(cls, model: InternalModel) -> bool:
        return isinstance(model, AppletFull)

    @classmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]:
        return [ActivityExport, ActivityFlowExport]

    async def export(self, model: AppletFull, expand: bool = False) -> dict:  # type: ignore  # noqa: E501
        ui, activity_flows = await asyncio.gather(
            self._build_ui_prop(model), self._build_activity_flows_prop(model)
        )
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: f"_:{self.str_to_id(model.display_name)}",
            LdKeyword.type: "reproschema:Protocol",
            "skos:prefLabel": model.display_name,
            "skos:altLabel": model.display_name,
            "schema:description": model.description,
            "landingPageContent": self._build_about(model),
            "landingPageType": "markdown",
            "schema:image": model.image,
            "schema:watermark": model.watermark,
            "schema:schemaVersion": self.schema_version,  # TODO load from extra  # noqa: E501
            "schema:version": model.version,
            "ui": ui,
            "activityFlows": activity_flows,
        }

        return await self._post_process(doc, expand)

    def _build_about(self, model: AppletFull):
        if model.about:
            about = []
            for lang, val in model.about.items():
                about.append({LdKeyword.language: lang, LdKeyword.value: val})
            return about
        return None

    async def _build_ui_prop(self, model: AppletFull) -> dict:
        order = []
        properties = []
        if model.activities:
            order_cors = []
            for i, activity in enumerate(model.activities):
                _id = (
                    f"_:{self.str_to_id(activity.name)}"  # TODO ensure uniques
                )
                _var = f"activity_{i}"  # TODO load from extra if exists

                processor = self.get_supported_processor(activity)
                order_cors.append(processor.export(activity))

                properties.append(
                    {
                        "isAbout": _id,
                        "prefLabel": activity.name,
                        "isVis": not activity.is_hidden,
                        "variableName": _var,
                    }
                )
            order = await asyncio.gather(*order_cors)

        return {
            "addProperties": properties,
            "order": order,
            # "shuffle": False,  # TODO from extra
        }

    async def _build_activity_flows_prop(self, model: AppletFull) -> dict:
        order = []
        properties = []
        if model.activity_flows:
            order_cors = []
            for i, flow in enumerate(model.activity_flows):
                _id = f"_:{self.str_to_id(flow.name)}"  # TODO ensure unique
                _var = f"flow_{i}"  # TODO load from extra if exists

                processor = self.get_supported_processor(flow)
                order_cors.append(processor.export(flow))
                properties.append(
                    {
                        "isAbout": _id,
                        "prefLabel": flow.name,
                        "isVis": not flow.is_hidden,
                        "variableName": _var,
                    }
                )

            order = await asyncio.gather(*order_cors)

        return {
            "activityFlowProperties": properties,
            "activityFlowOrder": list(order),
        }
