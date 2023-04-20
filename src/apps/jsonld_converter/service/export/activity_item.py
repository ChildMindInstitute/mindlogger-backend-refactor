from abc import abstractmethod

from apps.activities.domain.activity_full import (
    ActivityItemFull,
)
from apps.activities.domain.response_type_config import (
    ResponseType,
    SingleSelectionConfig,
    SliderConfig,
    TextConfig,
)
from apps.activities.domain.response_values import (
    SingleSelectionValues,
    SliderValues,
)
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
)
from apps.shared.domain import (
    InternalModel,
)


class ActivityItemBaseExport(BaseModelExport):
    @classmethod
    def supports(cls, model: InternalModel) -> bool:
        return isinstance(model, ActivityItemFull) and model.response_type == cls._get_supported_response_type()

    @classmethod
    @abstractmethod
    def _get_supported_response_type(cls) -> ResponseType:
        ...

    @abstractmethod
    def _get_input_type(self):
        ...

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: f"_:{model.id}",
            LdKeyword.type: "reproschema:Field",
            "name": model.name,
            "skos:prefLabel": model.name,
            "skos:altLabel": model.name,
            "question": model.question,
            "allowEdit": True,
            "ui": self._build_ui_prop(model)
        }
        response_options = self._build_response_options_prop(model)
        if response_options:
            doc["responseOptions"] = response_options

        return doc

    async def export(self, model: ActivityItemFull) -> dict:
        doc = self._build_doc(model)
        expanded = await self._expand(doc)

        return expanded[0]

    def _build_ui_prop(self, model: ActivityItemFull) -> dict:
        return {
            "inputType": self._get_input_type(),
            "allow": self._build_allow_prop(model)
        }

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = []
        if not model.config.remove_back_button:
            allow.append("disableBack")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        return None


class ActivityItemTextExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TEXT

    def _get_input_type(self):
        return 'text'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        if model.config.correct_answer_required and (correct_answer := model.config.correct_answer):
            doc["correctAnswer"] = correct_answer

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)
        if model.config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        config: TextConfig = model.config
        value_type = "xsd:string"
        if config.numerical_response_required:
            value_type = "xsd:integer"
        options = {
            "valueType": value_type,
            "removeBackOption": config.remove_back_button,
            "requiredValue": config.response_required,
            "isResponseIdentifier": config.response_data_identifier,
            "maxLength": config.max_response_length
        }

        return options


class ActivityItemSingleSelectExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SINGLESELECT

    def _get_input_type(self):
        return 'radio'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        additional_option = model.config.additional_response_option
        if additional_option:
            doc["isOptionalText"] = additional_option.text_input_option

        doc.update({
            "timer": model.config.timer * 1000  # set in milliseconds
        })

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)
        if model.config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        config: SingleSelectionConfig = model.config
        options = {
            "valueType": "xsd:anyURI",
            "removeBackOption": config.remove_back_button,
            "randomizeOptions": config.randomize_options,
            "scoring": config.add_scores,
            "responseAlert": config.set_alerts,
            "colorPalette": config.set_palette,
            "multipleChoice": False,
            "choices": self._build_choices_prop(model)

        }
        additional_option = config.additional_response_option
        if additional_option and additional_option.text_input_option:
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options

    def _build_choices_prop(self, model: ActivityItemFull) -> list:
        choices = []
        values: SingleSelectionValues = model.response_values
        for i, option in enumerate(values.options):
            choice = {
                "@type": "schema:option",
                "schema:name": option.text,
                # "schema:value": i,  # TODO value???
                "isVis": not option.is_hidden,
                "schema:color": option.color,
                "schema:description": option.tooltip,
                "schema:score": option.score,
                "schema:image": option.image,
                # "schema:alert": None  # TODO alert???
            }
            choices.append(choice)

        return choices


class ActivityItemMultipleSelectExport(ActivityItemSingleSelectExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.MULTISELECT

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        options = super()._build_response_options_prop(model)
        options["multipleChoice"] = True
        return options


class ActivityItemSliderExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SLIDER

    def _get_input_type(self):
        return 'slider'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        additional_option = model.config.additional_response_option
        if additional_option:
            doc["isOptionalText"] = additional_option.text_input_option

        doc.update({
            "timer": model.config.timer * 1000  # set in milliseconds
        })

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)
        if model.config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        config: SliderConfig = model.config
        values: SliderValues = model.response_values

        options = {
            "valueType": "xsd:integer",
            "removeBackOption": config.remove_back_button,
            "scoring": config.add_scores,
            "responseAlert": config.set_alerts,
            "choices": self._build_choices_prop(model),
            "continousSlider": config.continuous_slider,
            "tickLabel": config.show_tick_labels,
            # "textAnchors": true,  # TODO
            "tickMark": config.show_tick_marks,
            "schema:minValue": values.min_label,
            "schema:maxValue": values.max_label,
            "schema:minValueImg": values.min_image,
            "schema:maxValueImg": values.max_image,
        }
        additional_option = config.additional_response_option
        if additional_option and additional_option.text_input_option:
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options

    def _build_choices_prop(self, model: ActivityItemFull) -> list:
        choices = []
        values: SliderValues = model.response_values
        scores = values.scores
        for i, v in enumerate(range(values.min_value, values.max_value + 1)):
            lbl = str(v)
            image = None
            if v == values.min_value:
                lbl = values.min_label
                image = values.min_image
            elif v == values.max_value:
                lbl = values.max_label
                image = values.max_image
            choice = {
                "schema:name": lbl,
                "schema:value": v,
            }
            if scores:
                choice["schema:score"] = scores[i]
            if image:
                choice["schema:image"] = image

            choices.append(choice)

        return choices
