from abc import abstractmethod

from apps.activities.domain.activity_full import ActivityItemFull
from apps.activities.domain.response_type_config import (
    AudioPlayerConfig,
    DrawingConfig,
    ResponseType,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
)
from apps.activities.domain.response_values import (
    AudioPlayerValues,
    AudioValues,
    DrawingValues,
    NumberSelectionValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValues,
    SliderValues,
)
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.domain import ActivityItemExportData
from apps.jsonld_converter.service.export.base import BaseModelExport
from apps.shared.domain import InternalModel


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
            LdKeyword.id: self._build_id(model.name),  # TODO ensure unique
            LdKeyword.type: "reproschema:Field",
            "name": model.name,
            "skos:prefLabel": model.name,
            "skos:altLabel": model.name,
            "question": model.question,
            "allowEdit": True,
            "ui": self._build_ui_prop(model),
        }

        config = model.config
        if additional_option := getattr(config, "additional_response_option", None):
            doc["isOptionalText"] = additional_option.text_input_option

        if timer := getattr(config, "timer", None):
            doc.update({"timer": timer * 1000})  # set in milliseconds

        response_options = self._build_response_options_prop(model)
        if response_options:
            doc["responseOptions"] = response_options

        return doc

    async def export(  # type: ignore
        self, model: ActivityItemFull, expand: bool = False
    ) -> ActivityItemExportData:
        _id = self._build_id(model.name)  # TODO ensure unique
        doc = self._build_doc(model)

        data = await self._post_process(doc, expand)

        return ActivityItemExportData(id=_id, schema=data)

    def _build_ui_prop(self, model: ActivityItemFull) -> dict:
        return {
            "inputType": self._get_input_type(),
            "allow": self._build_allow_prop(model),
        }

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = []
        if getattr(model.config, "remove_back_button", False):
            allow.append("disableBack")
        if getattr(model.config, "skippable_item", False):
            allow.append("dontKnow")

        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        config = model.config
        options = {}
        if getattr(config, "remove_back_button", False):
            options["removeBackOption"] = True
        if additional_option := getattr(config, "additional_response_option", None):
            options["isOptionalTextRequired"] = additional_option.text_input_required

        return options


class ActivityItemTextExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TEXT

    def _get_input_type(self):
        return "text"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        config: TextConfig = model.config  # type: ignore[assignment]
        value_type = "xsd:string"
        if config.numerical_response_required:
            value_type = "xsd:integer"
        options.update(
            {
                "valueType": value_type,
                "requiredValue": config.response_required,
                "isResponseIdentifier": config.response_data_identifier,
                "maxLength": config.max_response_length,
            }
        )

        return options


class ActivityItemSingleSelectExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SINGLESELECT

    def _get_input_type(self):
        return "radio"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)
        config: SingleSelectionConfig = model.config  # type: ignore[assignment]  # noqa: E501
        options.update(
            {
                "valueType": "xsd:anyURI",  # todo tokens
                "randomizeOptions": config.randomize_options,
                "scoring": config.add_scores,
                "responseAlert": config.set_alerts,
                "colorPalette": config.set_palette,
                "multipleChoice": False,
                "choices": self._build_choices_prop(model),
            }
        )

        return options

    def _build_choices_prop(self, model: ActivityItemFull) -> list:
        choices = []
        values: SingleSelectionValues = model.response_values  # type: ignore[assignment]  # noqa: E501
        for i, option in enumerate(values.options):
            choice = {
                LdKeyword.type: "schema:option",
                "schema:name": option.text,
                # "schema:value": i,  # TODO value???
                # is_vis means is_hidden
                "isVis": option.is_hidden,
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

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)
        options["multipleChoice"] = True

        return options


class SliderValuesMixin:
    def _build_choices_prop(self, values: SliderValues) -> list:
        choices = []
        scores = values.scores
        for i, v in enumerate(range(values.min_value, values.max_value + 1)):
            lbl: str | None = str(v)
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


class ActivityItemSliderExport(ActivityItemBaseExport, SliderValuesMixin):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SLIDER

    def _get_input_type(self):
        return "slider"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        config: SliderConfig = model.config  # type: ignore[assignment]
        values: SliderValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        options.update(
            {
                "valueType": "xsd:integer",
                "scoring": config.add_scores,
                "responseAlert": config.set_alerts,
                "choices": self._build_choices_prop(values),
                "continousSlider": config.continuous_slider,
                "tickLabel": config.show_tick_labels,
                # "textAnchors": true,  # TODO
                "tickMark": config.show_tick_marks,
                "schema:minValue": values.min_label,
                "schema:maxValue": values.max_label,
                "schema:minValueImg": values.min_image,
                "schema:maxValueImg": values.max_image,
                "minAlertValue": 0,  # TODO
                "maxAlertValue": 0,  # TODO
                "responseAlertMessage": "",  # TODO
            }
        )

        return options


class ActivityItemSliderRowsExport(ActivityItemBaseExport, SliderValuesMixin):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SLIDERROWS

    def _get_input_type(self):
        return "stackedSlider"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        config: SliderRowsConfig = model.config  # type: ignore[assignment]
        values: SliderRowsValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        slider_options = []
        for row in values.rows:
            option = {
                "schema:sliderLabel": row.label,
                "schema:minValue": row.min_label,
                "schema:maxValue": row.max_label,
                "schema:minValueImg": row.min_image,
                "schema:maxValueImg": row.max_image,
                "choices": self._build_choices_prop(row),
            }
            slider_options.append(option)

        options.update(
            {
                "valueType": "xsd:integer",
                "scoring": config.add_scores,
                "responseAlert": config.set_alerts,
                "sliderOptions": slider_options,
            }
        )

        return options


class ActivityItemMessageExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.MESSAGE

    def _get_input_type(self):
        return "markdownMessage"


class ActivityItemNumberExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.NUMBERSELECT

    def _get_input_type(self):
        return "ageSelector"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        values: NumberSelectionValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        options.update(
            {
                "schema:minAge": values.min_value,
                "schema:maxAge": values.max_value,
                "minValue": values.min_value,
                "maxValue": values.max_value,
            }
        )

        return options


class ActivityItemDateExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.DATE

    def _get_input_type(self):
        return "date"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)
        options.update(
            {
                "valueType": "xsd:date",
                "requiredValue": True,
                "schema:maxValue": "new Date()",
            }
        )

        return options


class ActivityItemTimeExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TIME

    def _get_input_type(self):
        return "time"


class ActivityItemTimeRangeExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TIMERANGE

    def _get_input_type(self):
        return "timeRange"


class ActivityItemGeolocationExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.GEOLOCATION

    def _get_input_type(self):
        return "geolocation"


class ActivityItemAudioExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.AUDIO

    def _get_input_type(self):
        return "audio"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        values: AudioValues = model.response_values  # type: ignore[assignment]
        options.update(
            {
                "schema:maxValue": values.max_duration * 1000,  # milliseconds
                "schema:minValue": 0,
            }
        )

        return options


class ActivityItemPhotoExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.PHOTO

    def _get_input_type(self):
        return "photo"


class ActivityItemVideoExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.VIDEO

    def _get_input_type(self):
        return "video"


class ActivityItemDrawingExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.DRAWING

    def _get_input_type(self):
        return "drawing"

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)

        values: DrawingValues = model.response_values  # type: ignore[assignment]  # noqa: E501
        # TODO inputOptions in UI by context but in index by legacy
        if bg_img := values.drawing_example:
            doc["inputOptions"] = [
                {
                    LdKeyword.type: "http://schema.org/URL",
                    "schema:name": "backgroundImage",
                    "schema:value": bg_img,
                }
            ]

        return doc

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)

        config: DrawingConfig = model.config  # type: ignore[assignment]
        values: DrawingValues = model.response_values  # type: ignore[assignment]  # noqa: E501
        options.update(
            {
                "removeUndoOption": config.remove_undo_button,
                "topNavigationOption": config.navigation_to_top,
            }
        )
        if example_img := values.drawing_example:
            options["schema:image"] = example_img

        return options


class ActivityItemAudioPlayerExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.AUDIOPLAYER

    def _get_input_type(self):
        return "audioStimulus"

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)

        config: AudioPlayerConfig = model.config  # type: ignore[assignment]
        values: AudioPlayerValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        doc["media"] = {
            values.file: {
                "schema:name": "stimulus",
                "schema:contentUrl": values.file,
            }
        }

        # TODO inputOptions in UI by context but in index by legacy
        doc["inputOptions"] = [
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
            },
        ]

        return doc


class ActivityItemSingleSelectionRowsExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.SINGLESELECTROWS

    def _get_input_type(self):
        return "stackedRadio"

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)
        config: SingleSelectionRowsConfig = model.config  # type: ignore[assignment]  # noqa: E501
        options.update(
            {
                "valueType": "xsd:anyURI",  # todo tokens
                "scoring": config.add_scores,
                "responseAlert": config.set_alerts,
                "multipleChoice": False,
                "options": self._build_options(model),
                "itemList": self._build_items(model),
                "itemOptions": self._build_item_options(model),
            }
        )

        return options

    def _build_options(self, model: ActivityItemFull) -> list[dict]:
        values: SingleSelectionRowsValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        options = []
        for opt in values.options:
            option = {
                "schema:description": opt.tooltip,
                "schema:image": opt.image,
                "schema:name": opt.text,
            }
            options.append(option)

        return options

    def _build_items(self, model: ActivityItemFull) -> list[dict]:
        values: SingleSelectionRowsValues = model.response_values  # type: ignore[assignment]  # noqa: E501

        items = []
        for itm in values.rows:
            item = {
                "schema:name": itm.row_name,
                "schema:image": itm.row_image,
                "schema:description": itm.tooltip,
            }
            items.append(item)

        return items

    def _build_item_options(self, model: ActivityItemFull):
        values: SingleSelectionRowsValues = model.response_values  # type: ignore[assignment]  # noqa: E501
        item_options = []
        if values.data_matrix:
            for itm in values.data_matrix:
                row = []
                for opt in itm.options:
                    col = {
                        "schema:score": opt.score,
                        "schema:alert": opt.alert,
                    }
                    row.append(col)
                item_options.append(row)

        return item_options


class ActivityItemMultiSelectionRowsExport(ActivityItemSingleSelectionRowsExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.MULTISELECTROWS

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict:
        options = super()._build_response_options_prop(model)
        options["multipleChoice"] = True

        return options
