import asyncio
from typing import Type

from apps.activities.domain.activity_full import ActivityFull, ActivityItemFull
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.domain import ActivityExportData
from apps.jsonld_converter.service.export import (
    ActivityItemAudioExport,
    ActivityItemAudioPlayerExport,
    ActivityItemDateExport,
    ActivityItemDrawingExport,
    ActivityItemGeolocationExport,
    ActivityItemMessageExport,
    ActivityItemMultipleSelectExport,
    ActivityItemMultiSelectionRowsExport,
    ActivityItemNumberExport,
    ActivityItemPhotoExport,
    ActivityItemSingleSelectExport,
    ActivityItemSingleSelectionRowsExport,
    ActivityItemSliderExport,
    ActivityItemSliderRowsExport,
    ActivityItemTextExport,
    ActivityItemTimeExport,
    ActivityItemTimeRangeExport,
    ActivityItemVideoExport,
)
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
    ContainsNestedModelMixin,
)
from apps.jsonld_converter.service.export.conditional_logic import (
    export_conditional_logic,
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
            ActivityItemSingleSelectionRowsExport,
            ActivityItemMultiSelectionRowsExport,
        ]

    async def export(
        self, model: ActivityFull, expand: bool = False
    ) -> ActivityExportData:  # type: ignore  # noqa: E501
        ui = await self._build_ui_prop(model)
        _id = self._build_id(model.name)
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: _id,  # TODO ensure uniques  # noqa: E501
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

        coros = []
        for item in model.items:
            processor = self.get_supported_processor(item)
            coros.append(processor.export(item))

        *items, data = await asyncio.gather(
            *coros, self._post_process(doc, expand)
        )

        return ActivityExportData(id=_id, schema=data, activity_items=items)

    def _build_item_is_vis(self, item: ActivityItemFull) -> bool | str:
        if item.conditional_logic:
            return export_conditional_logic(item.conditional_logic)

        return not item.is_hidden

    async def _build_ui_prop(self, model: ActivityFull) -> dict:
        order = []
        properties = []
        if model.items:
            for i, item in enumerate(model.items):
                _id = self._build_id(item.name)  # TODO ensure unique
                _var = self._build_id(item.name, None)  # TODO ensure unique

                properties.append(
                    {
                        "isAbout": _id,
                        "prefLabel": item.name,
                        "isVis": self._build_item_is_vis(item),
                        "variableName": _var,
                    }
                )
                order.append(_id)

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
