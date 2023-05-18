import asyncio
from typing import Type

from apps.activities.domain.activity_full import ActivityFull
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.export import (
    ActivityItemTextExport,
    ActivityItemSingleSelectExport,
    ActivityItemMultipleSelectExport,
    ActivityItemSliderExport,
    ActivityItemMessageExport,
    ActivityItemNumberExport,
    ActivityItemDateExport,
    ActivityItemTimeExport,
    ActivityItemTimeRangeExport,
    ActivityItemGeolocationExport,
    ActivityItemAudioExport,
    ActivityItemPhotoExport,
    ActivityItemVideoExport,
    ActivityItemDrawingExport,
    ActivityItemAudioPlayerExport,
    ActivityItemSliderRowsExport,
)
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
    ContainsNestedModelMixin,
)
from apps.shared.domain import InternalModel


class ActivityExport(BaseModelExport, ContainsNestedModelMixin):
    @classmethod
    def supports(cls, model: InternalModel) -> bool:
        return isinstance(model, ActivityFull)

    @classmethod
    def get_supported_types(cls) -> list[Type["BaseModelExport"]]:
        return [
            ActivityItemTextExport,
            ActivityItemSingleSelectExport,
            ActivityItemMultipleSelectExport,
            ActivityItemSliderExport,
            ActivityItemSliderRowsExport,
            ActivityItemMessageExport,
            ActivityItemNumberExport,
            ActivityItemDateExport,
            ActivityItemTimeExport,
            ActivityItemTimeRangeExport,
            ActivityItemGeolocationExport,
            ActivityItemAudioExport,
            ActivityItemPhotoExport,
            ActivityItemVideoExport,
            ActivityItemDrawingExport,
            ActivityItemAudioPlayerExport,
        ]

    async def export(self, model: ActivityFull, expand: bool = False) -> dict:
        ui = await self._build_ui_prop(model)
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: f"_:{self.str_to_id(model.name)}",  # TODO ensure uniques
            LdKeyword.type: "reproschema:Activity",
            "skos:prefLabel": model.name,
            "skos:altLabel": model.name,
            "schema:description": model.description,
            "schema:image": model.image,
            "schema:splash": model.splash_screen,
            "isReviewerActivity": model.is_reviewable,
            "isOnePageAssessment": model.show_all_at_once,
            "ui": ui,
        }

        return await self._post_process(doc, expand)

    async def _build_ui_prop(self, model: ActivityFull) -> dict:
        order = []
        properties = []
        if model.items:
            order_cors = []
            for i, item in enumerate(model.items):
                _id = f"_:{self.str_to_id(item.name)}"  # TODO ensure uniques
                _var = f"item_{i}"  # TODO load from extra if exists

                processor = self.get_supported_processor(item)
                order_cors.append(processor.export(item))

                properties.append({
                    "isAbout": _id,
                    "prefLabel": item.name,
                    "isVis": not item.is_hidden,
                    "variableName": _var
                })
            order = await asyncio.gather(*order_cors)

        return {
            "addProperties": properties,
            "order": order,
            "allow": self._build_allow_prop(model),
            # "shuffle": False,  # TODO from extra???
        }

    def _build_allow_prop(self, model: ActivityFull) -> list[str]:
        allow = []
        if not model.response_is_editable:
            allow.append("disableBack")
        if model.is_skippable:
            allow.append("skipped")
        return allow
