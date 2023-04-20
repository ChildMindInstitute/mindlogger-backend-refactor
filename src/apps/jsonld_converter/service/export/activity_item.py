from abc import (
    abstractmethod,
    ABC,
)

from apps.activities.domain.activity_full import (
    ActivityItemFull,
)
from apps.activities.domain.response_type_config import (
    ResponseType,
    SingleSelectionConfig,
    SliderConfig,
    TextConfig,
    NumberSelectionConfig,
    DefaultConfig,
    DrawingConfig,
    AudioPlayerConfig,
)
from apps.activities.domain.response_values import (
    SingleSelectionValues,
    SliderValues,
    NumberSelectionValues,
    AudioValues,
    DrawingValues,
    AudioPlayerValues,
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
        if model.config.remove_back_button:
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

        if model.config.timer:
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
                LdKeyword.type: "schema:option",
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

        if model.config.timer:
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


class ActivityItemMessageExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.MESSAGE

    def _get_input_type(self):
        return 'markdownMessage'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        if model.config.timer:
            doc.update({
                "timer": model.config.timer * 1000  # set in milliseconds
            })

        return doc


class ActivityItemNumberExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.NUMBERSELECT

    def _get_input_type(self):
        return 'ageSelector'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        config: NumberSelectionConfig = model.config
        additional_option = config.additional_response_option
        if additional_option:
            doc["isOptionalText"] = additional_option.text_input_option

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)
        if model.config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        config: NumberSelectionConfig = model.config
        values: NumberSelectionValues = model.response_values

        options = {
            "schema:minAge": values.min_value,
            "schema:maxAge": values.max_value,
            "minValue": values.min_value,
            "maxValue": values.max_value,
            "removeBackOption": config.remove_back_button,
        }
        additional_option = config.additional_response_option
        if additional_option and additional_option.text_input_option:
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options


class ActivityItemDefaultConfigExport(ActivityItemBaseExport, ABC):

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        config: DefaultConfig = model.config
        additional_option = config.additional_response_option
        if additional_option:
            doc["isOptionalText"] = additional_option.text_input_option

        if config.timer:
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
        config: DefaultConfig = model.config
        options = {
            "removeBackOption": config.remove_back_button,
        }
        additional_option = config.additional_response_option
        if additional_option and additional_option.text_input_option:
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options


class ActivityItemDateExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.DATE

    def _get_input_type(self):
        return 'date'

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        options = super()._build_response_options_prop(model)
        options.update({
            "valueType": "xsd:date",
            "requiredValue": True,
            "schema:maxValue": "new Date()",
        })

        return options


class ActivityItemTimeRangeExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TIMERANGE

    def _get_input_type(self):
        return 'timeRange'


class ActivityItemGeolocationExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.GEOLOCATION

    def _get_input_type(self):
        return 'geolocation'


class ActivityItemAudioExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.AUDIO

    def _get_input_type(self):
        return 'audio'

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        options = super()._build_response_options_prop(model)
        values: AudioValues = model.response_values
        options.update({
            "schema:maxValue": values.max_duration * 1000,  # milliseconds
            "schema:minValue": 0
        })

        return options


class ActivityItemPhotoExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.PHOTO

    def _get_input_type(self):
        return 'photo'


class ActivityItemVideoExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.VIDEO

    def _get_input_type(self):
        return 'video'


class ActivityItemDrawingExport(ActivityItemDefaultConfigExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.DRAWING

    def _get_input_type(self):
        return 'drawing'

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        options = super()._build_response_options_prop(model)

        config: DrawingConfig = model.config
        values: DrawingValues = model.response_values
        options.update({
            "removeUndoOption": config.remove_undo_button,
            "topNavigationOption": config.navigation_to_top,
        })
        if example_img := values.drawing_example:
            options["schema:image"] = example_img

        return options

    def _build_ui_prop(self, model: ActivityItemFull) -> dict:
        ui = super()._build_ui_prop(model)

        values: DrawingValues = model.response_values
        if bg_img := values.drawing_example:
            ui["inputOptions"] = [
                {
                    LdKeyword.type: "http://schema.org/URL",
                    "schema:name": "backgroundImage",
                    "schema:value": bg_img,
                }
            ]

        return ui


class ActivityItemAudioPlayerExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.AUDIOPLAYER

    def _get_input_type(self):
        return 'audioStimulus'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)

        config: AudioPlayerConfig = model.config
        values: AudioPlayerValues = model.response_values

        additional_option = config.additional_response_option
        if additional_option:
            doc["isOptionalText"] = additional_option.text_input_option

        doc["media"] = {
            values.file: {
                "schema:name": "stimulus",
                "schema:contentUrl": values.file
            }
        }

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)

        config: AudioPlayerConfig = model.config
        if config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        config: AudioPlayerConfig = model.config
        options = {
            "removeBackOption": config.remove_back_button,
        }
        additional_option = config.additional_response_option
        if additional_option and additional_option.text_input_option:
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options

    def _build_ui_prop(self, model: ActivityItemFull) -> dict:
        ui = super()._build_ui_prop(model)

        config: AudioPlayerConfig = model.config
        values: AudioPlayerValues = model.response_values
        ui["inputOptions"] = [
            {
                LdKeyword.type: "http://schema.org/URL",
                "schema:name": "stimulus",
                "schema:value": values.file,
                "schema:contentUrl": values.file,
            },
            {
                LdKeyword.type: "http://schema.org/Boolean",
                "schema:name": "allowReplay",
                "schema:value": not config.play_once,
            }
        ]

        return ui
