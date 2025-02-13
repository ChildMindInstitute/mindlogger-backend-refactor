import dataclasses
import uuid
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Type

from pydantic.color import Color

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.conditions import AnyCondition, ConditionType
from apps.activities.domain.response_type_config import (
    ABTrailsConfig,
    ABTrailsDeviceType,
    ABTrailsOrder,
    AdditionalResponseOption,
    AudioConfig,
    AudioPlayerConfig,
    BlockConfiguration,
    BlockType,
    ButtonConfiguration,
    DateConfig,
    DrawingConfig,
    FixationScreen,
    FlankerConfig,
    GeolocationConfig,
    InputType,
    MessageConfig,
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    NumberSelectionConfig,
    Phase,
    PhotoConfig,
    ResponseType,
    ResponseTypeConfig,
    SamplingMethod,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    StabilityTrackerConfig,
    StimulusConfiguration,
    TextConfig,
    TimeConfig,
    TimeRangeConfig,
    VideoConfig,
)
from apps.activities.domain.response_values import (
    AudioPlayerValues,
    AudioValues,
    DrawingValues,
    MultiSelectionRowsValues,
    MultiSelectionValues,
    NumberSelectionValues,
    ResponseValueConfig,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValue,
    SliderRowsValues,
    SliderValueAlert,
    SliderValues,
    _SingleSelectionDataOption,
    _SingleSelectionDataRow,
    _SingleSelectionOption,
    _SingleSelectionRow,
    _SingleSelectionValue,
)
from apps.jsonld_converter.errors import JsonLDStructureError
from apps.jsonld_converter.service.base import str_to_id
from apps.jsonld_converter.service.document.base import CommonFieldsMixin, LdDocumentBase, LdKeyword, OrderAware
from apps.jsonld_converter.service.document.conditional_logic import (
    ConditionData,
    ConditionOptionResolver,
    ConditionValueResolver,
    ResolvesConditionalLogic,
)


class ReproFieldBase(LdDocumentBase, CommonFieldsMixin, ResolvesConditionalLogic):
    CFG_TYPE: Type[ResponseTypeConfig] | None = None
    RESPONSE_TYPE: ResponseType

    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_image: str | None = None
    ld_question: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None
    ld_allow_edit: bool | None = None
    ld_remove_back_option: bool | None = None
    ld_is_optional_text: bool | None = None
    ld_is_optional_text_required: bool | None = None
    ld_timer: int | None = None

    extra: dict | None = None
    is_skippable: bool = False

    @classmethod
    @abstractmethod
    def _get_supported_input_types(cls) -> list[str]: ...

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            "reproschema:Field",
            *cls.attr_processor.resolve_key("reproschema:Field"),
        ]
        _type = cls.attr_processor.first(doc.get(LdKeyword.type))
        _input_type = cls.attr_processor.get_attr_value(doc, "reproschema:inputType")
        if not _input_type:
            # try fetch from compact
            _input_type = doc.get("ui", {}).get("inputType")

        return _type in ld_types and _input_type in cls._get_supported_input_types()

    @property
    def name(self):
        name = self.ld_pref_label or self.ld_id or self.ld_alt_label  # TODO: discuss
        return str_to_id(name, r"\s")

    def _get_ld_question(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, "schema:question", drop=drop)

    def _get_ld_readonly(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, "schema:readonlyValue", drop=drop)

    def _get_ld_is_multiple(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, "reproschema:multipleChoice", drop=drop)

    def _get_choice_value(self, doc: dict, drop=False):
        for attr in ["reproschema:value", "schema:value"]:
            if (res := self.attr_processor.get_attr_value(doc, attr, drop=drop)) is not None:
                break

        return res

    def _value_or_none(self, doc: dict, key: str):
        value = self.attr_processor.get_attr_value(doc, key)
        return value if value != "false" else None

    def _format_choice(self, doc: dict):
        choice = {
            "name": self.attr_processor.get_translation(doc, "schema:name", self.lang),
            "value": self._get_choice_value(doc),
            "image": self._get_ld_image(doc),
            "is_vis": self._is_visible(doc),
            "alert": self.attr_processor.get_translation(doc, "schema:alert", self.lang)
            if self.attr_processor.get_translation(doc, "schema:alert", self.lang) != ""
            else None,
            "color": self._value_or_none(doc, "schema:color"),
            "tooltip": self._value_or_none(doc, "schema:description"),
            "score": self.attr_processor.get_attr_value(doc, "schema:score"),
        }
        return choice

    def _get_ld_choices_formatted(self, doc: dict, drop=False, keys: list[str] | None = None) -> list[dict] | None:
        keys = keys or ["reproschema:choices", "schema:itemListElement"]
        choices = []

        for key in keys:
            if obj_list := self.attr_processor.get_attr_list(doc, key, drop=drop):
                for obj in obj_list:
                    choice = self._format_choice(obj)
                    choices.append(choice)
                break

        return choices

    async def _get_ld_response_options_doc(self, doc: dict, drop=False, term_attr: str | None = None):
        term_attr = term_attr or "reproschema:responseOptions"
        key = self.attr_processor.get_key(doc, term_attr)
        options_doc = self.attr_processor.get_attr_single(doc, term_attr)
        if options_doc and len(options_doc) == 1 and LdKeyword.id in options_doc:
            try:
                options_id = options_doc[LdKeyword.id]
            except KeyError as e:
                raise JsonLDStructureError(f"{LdKeyword.id} missed in doc", doc) from e

            options_doc = await self._expand(options_id, self.base_url)
            if isinstance(options_doc, list):
                options_doc = options_doc[0]

        if drop and key:
            del doc[key]

        return options_doc

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        self.ld_pref_label = self._get_ld_pref_label(processed_doc, drop=True)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc, drop=True)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_question = self._get_ld_question(processed_doc, drop=True)
        self.ld_is_vis = self._is_visible(processed_doc, drop=True)
        self.ld_allow_edit = self.attr_processor.get_attr_value(processed_doc, "reproschema:allowEdit", drop=True)

        self.ld_is_optional_text = self.attr_processor.get_attr_value(
            processed_doc, "reproschema:isOptionalText", drop=True
        )
        self.ld_timer = self._get_timer(processed_doc, drop=True)

        allow_list = self._get_allow_list(processed_doc, drop=True)
        self._to_extra("allow_list", allow_list, "fields")
        self.is_skippable = self._is_skippable(allow_list)

        options_doc = await self._get_ld_response_options_doc(processed_doc, drop=True)
        if options_doc:
            await self._process_ld_response_options(options_doc)
        self.ld_variable_name = self.name

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        await self._load_from_processed_doc(processed_doc, base_url)
        self._load_extra(processed_doc)

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        self.ld_is_optional_text_required = self.attr_processor.get_attr_value(
            options_doc, "reproschema:isOptionalTextRequired"
        )
        self.ld_remove_back_option = self.attr_processor.get_attr_value(options_doc, "reproschema:removeBackOption")

    def _build_config(self, _cls: Type | None, **attrs):
        assert _cls is not None
        if self.ld_is_optional_text:
            additional_response_option = AdditionalResponseOption(
                text_input_option=True,
                text_input_required=bool(self.ld_is_optional_text_required),
            )
        else:
            additional_response_option = AdditionalResponseOption(
                text_input_option=False,
                text_input_required=False,
            )

        config = _cls(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            additional_response_option=additional_response_option,
            timer=int(self.ld_timer / 1000) if self.ld_timer else None,
            **attrs,
        )

        return config

    def _build_response_values(self) -> ResponseValueConfig | None:
        return None

    def resolve_condition_name(self):
        return self.name

    def resolve_condition(self, condition: ConditionData) -> AnyCondition:
        """
        Resolve ConditionData of item to Condition
        """
        raise NotImplementedError(f'Condition type "{condition.type}" not supported')

    def _load_extra(self, doc: dict):
        to_remove = ["reproschema:inputType"]
        for attr in to_remove:
            if key := self.attr_processor.get_key(doc, attr):
                del doc[key]
        super()._load_extra(doc)

    def export(self) -> ActivityItemCreate:
        cfg_cls = self.CFG_TYPE
        config = self._build_config(cfg_cls)
        response_values = self._build_response_values()
        allow_edit = True
        if self.ld_allow_edit is not None:
            allow_edit = bool(self.ld_allow_edit)
        return ActivityItemCreate(
            question=self.ld_question or {},
            response_type=self.RESPONSE_TYPE,
            response_values=response_values,
            config=config,
            name=self.name,
            is_hidden=self.ld_is_vis is False,
            extra_fields=self.extra,
            allow_edit=allow_edit,
        )


class ReproFieldText(ReproFieldBase):
    INPUT_TYPE = "text"
    RESPONSE_TYPE = ResponseType.TEXT

    ld_correct_answer: str | None = None
    ld_is_response_identifier: bool | None = None
    ld_max_length: int | None = None
    ld_value_type: str | None = None
    ld_required_value: bool | None = None

    is_multiple: bool = False
    choices: list[dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        self.ld_correct_answer = self.attr_processor.get_translation(processed_doc, "schema:correctAnswer", self.lang)

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_is_response_identifier = self.attr_processor.get_attr_value(
            options_doc, "reproschema:isResponseIdentifier"
        )
        self.ld_max_length = self.attr_processor.get_attr_value(options_doc, "reproschema:maxLength")
        self.ld_required_value = self.attr_processor.get_attr_value(options_doc, "reproschema:requiredValue")
        self.ld_value_type = self.attr_processor.get_attr_single(
            options_doc, "reproschema:valueType", ld_key=LdKeyword.id
        )

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _build_config(self, _cls: Type | None, **attrs):
        numerical_response_required = False
        if self.ld_value_type and self.attr_processor.is_equal_term_val(self.ld_value_type, "xsd:integer"):
            numerical_response_required = True

        config = TextConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            correct_answer_required=self.ld_correct_answer not in [None, ""],
            correct_answer=self.ld_correct_answer or None,
            numerical_response_required=numerical_response_required,
            response_data_identifier=bool(self.ld_is_response_identifier),
            response_required=bool(self.ld_required_value),
        )
        if self.ld_max_length:
            config.max_response_length = self.ld_max_length

        return config


class ReproFieldRadio(ReproFieldBase):
    INPUT_TYPE = "radio"
    RESPONSE_TYPE = ResponseType.SINGLESELECT

    ld_color_palette: bool | None = None
    ld_randomize_options: bool | None = None
    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None
    ld_is_response_identifier: bool | None = None

    is_multiple: bool = False
    choices: list[dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_color_palette = self.attr_processor.get_attr_value(options_doc, "reproschema:colorPalette")
        self.ld_randomize_options = self.attr_processor.get_attr_value(options_doc, "reproschema:randomizeOptions")
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, "reproschema:scoring")
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, "reproschema:responseAlert")

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _build_config(self, _cls: Type | None, **attrs):
        args = dict(
            randomize_options=bool(self.ld_randomize_options),  # TODO use allow?
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            add_tooltip=False,  # TODO
            set_palette=bool(self.ld_color_palette),  # TODO
            response_data_identifier=bool(self.ld_is_response_identifier) if not self.is_multiple else None,
        )
        cfg_cls = MultiSelectionConfig if self.is_multiple else SingleSelectionConfig

        return super()._build_config(cfg_cls, **args)

    def _build_response_values(self) -> ResponseValueConfig | None:
        values = []
        for choice in self.choices or []:
            color = None
            if color_val := choice.get("color"):
                color = Color(color_val)  # TODO process error

            values.append(
                # TODO tokens
                _SingleSelectionValue(
                    text=choice.get("name"),
                    value=choice.get("value"),
                    image=choice.get("image"),
                    score=choice.get("score") if bool(self.ld_scoring) else None,
                    tooltip=choice.get("tooltip"),
                    # is_vis means is_hidden
                    is_hidden=choice.get("is_vis", False) or False,
                    color=color,
                    alert=choice.get("alert"),
                )
            )
        _cls: Type[MultiSelectionValues | SingleSelectionValues] = (
            MultiSelectionValues if self.is_multiple else SingleSelectionValues
        )
        # TODO palette name
        response_values = _cls(options=values)

        return response_values

    def resolve_condition(self, condition: ConditionData) -> AnyCondition:
        if self.is_multiple:
            # checkbox
            if condition.type not in (
                ConditionType.INCLUDES_OPTION,
                ConditionType.NOT_INCLUDES_OPTION,
            ):
                raise NotImplementedError(f'Condition type "{condition.type}" not supported')
        else:
            # radio
            if condition.type not in (
                ConditionType.EQUAL,
                ConditionType.NOT_EQUAL,
            ):
                raise NotImplementedError(f'Condition type "{condition.type}" not supported')

        return ConditionOptionResolver().resolve(self.name, condition)

    def export(self) -> ActivityItemCreate:
        if self.is_multiple:
            self.RESPONSE_TYPE = ResponseType.MULTISELECT
        return super().export()


class ReproFieldRadioStacked(ReproFieldBase):
    INPUT_TYPE = "stackedRadio"
    RESPONSE_TYPE = ResponseType.SINGLESELECTROWS

    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None
    ld_item_list: list[dict] | None = None
    ld_options: list[dict] | None = None
    ld_item_options: list[dict] | None = None

    is_multiple: bool = False
    choices: list[dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, "reproschema:scoring")
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, "reproschema:responseAlert")

        self.ld_item_list = self._get_ld_choices_formatted(options_doc, keys=["reproschema:itemList"])
        self.ld_options = self._get_ld_choices_formatted(options_doc, keys=["reproschema:options"])
        self.ld_item_options = self._get_ld_choices_formatted(options_doc, keys=["reproschema:itemOptions"])

    def _build_config(self, _cls: Type | None, **attrs):
        cfg_cls = MultiSelectionRowsConfig if self.is_multiple else SingleSelectionRowsConfig

        add_tooltip = any(bool(opt.get("tooltip")) for opt in [*(self.ld_options or []), *(self.ld_item_list or [])])

        config = cfg_cls(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            timer=int(self.ld_timer / 1000) if self.ld_timer else None,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            add_tooltip=add_tooltip,
        )

        return config

    def _build_response_values(self) -> ResponseValueConfig | None:
        items = self.ld_item_list or []
        choices = self.ld_options or []
        item_options = self.ld_item_options or []

        if item_options == []:
            for choice in choices:
                for item in items:
                    item_options.append(
                        {
                            "name": None,
                            "value": None,
                            "image": None,
                            "is_vis": None,
                            "alert": None,
                            "color": None,
                            "tooltip": None,
                            "score": None,
                        }
                    )

        if len(item_options) != len(items) * len(choices):
            raise Exception("Item options doesn't match items and options data")

        chunk_size = len(choices)
        vals = [
            # fmt: off
            item_options[i : i + chunk_size]
            for i in range(0, len(item_options), chunk_size)
            # fmt: on
        ]

        rows = []
        for item in items:
            row = _SingleSelectionRow(
                id=str(uuid.uuid4()),
                row_name=item.get("name"),
                row_image=item.get("image") or None,
                tooltip=item.get("tooltip") or None,
            )
            rows.append(row)

        options = []
        for choice in choices:
            option = _SingleSelectionOption(
                id=str(uuid.uuid4()),
                text=choice.get("name"),
                image=choice.get("image") or None,
                tooltip=choice.get("tooltip") or None,
            )
            options.append(option)

        data_matrix = []
        for i, row_vals in enumerate(vals):
            _options = []
            for j, val in enumerate(row_vals):
                # fmt: off
                _score = val.get("score") if bool(self.ld_scoring) else None  # noqa: E501
                _alert = val.get("alert") if bool(self.ld_response_alert) else None  # noqa: E501
                _option = _SingleSelectionDataOption(
                    # TODO tooltip, value missed
                    option_id=options[j].id,
                    score=_score,
                    alert=_alert,
                    value=None,  # TODO
                )
                # fmt: on
                _options.append(_option)

            data_matrix.append(_SingleSelectionDataRow(row_id=rows[i].id, options=_options))

        _cls = MultiSelectionRowsValues if self.is_multiple else SingleSelectionRowsValues
        response_values = _cls(rows=rows, options=options, data_matrix=data_matrix)

        return response_values

    def export(self) -> ActivityItemCreate:
        if self.is_multiple:
            self.RESPONSE_TYPE = ResponseType.MULTISELECTROWS
        return super().export()


@dataclasses.dataclass
class LdSliderOption:
    ld_label: str | None = None
    ld_min_value: str | None = None
    ld_max_value: str | None = None
    ld_min_value_img: str | None = None
    ld_max_value_img: str | None = None
    choices: list[dict] | None = None


class ReproFieldSliderBase(ReproFieldBase, ABC):
    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None
    ld_response_alert_message: str | None = None
    ld_response_alert_min_value: int | None = None
    ld_response_alert_max_value: int | None = None

    def _get_slider_option(self, doc: dict) -> LdSliderOption:
        option = LdSliderOption(
            ld_label=self.attr_processor.get_translation(doc, "schema:sliderLabel", self.lang),
            ld_min_value=self.attr_processor.get_attr_value(doc, "schema:minValue"),
            ld_max_value=self.attr_processor.get_attr_value(doc, "schema:maxValue"),
            # fmt: off
            ld_min_value_img=self.attr_processor.get_attr_value(doc, "schema:minValueImg") or None,
            ld_max_value_img=self.attr_processor.get_attr_value(doc, "schema:maxValueImg") or None,
            # fmt: on
            choices=self._get_ld_choices_formatted(doc),
        )
        return option

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, "reproschema:scoring")
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, "reproschema:responseAlert")
        self.ld_response_alert_message = self.attr_processor.get_attr_value(options_doc, "schema:responseAlertMessage")
        self.ld_response_alert_min_value = self.attr_processor.get_attr_value(options_doc, "schema:minAlertValue")
        self.ld_response_alert_max_value = self.attr_processor.get_attr_value(options_doc, "schema:maxAlertValue")


class ReproFieldSlider(ReproFieldSliderBase):
    INPUT_TYPE = "slider"
    RESPONSE_TYPE = ResponseType.SLIDER
    CFG_TYPE = SliderConfig

    ld_tick_label: bool | None = None
    ld_tick_mark: bool | None = None
    ld_continuous_slider: bool | None = None

    slider_option: LdSliderOption | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.slider_option = self._get_slider_option(options_doc)

        self.ld_tick_label = self.attr_processor.get_attr_value(options_doc, "reproschema:tickLabel")
        self.ld_tick_mark = self.attr_processor.get_attr_value(options_doc, "reproschema:tickMark")
        self.ld_continuous_slider = self.attr_processor.get_attr_value(options_doc, "reproschema:continousSlider")

    def _build_config(self, _cls: Type | None, **attrs):
        attrs = dict(
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            show_tick_marks=bool(self.ld_tick_mark),
            show_tick_labels=bool(self.ld_tick_label),
            continuous_slider=bool(self.ld_continuous_slider),
        )
        return super()._build_config(_cls, **attrs)

    def _build_response_values(self) -> ResponseValueConfig | None:
        assert self.slider_option is not None

        first_choice: dict = {}
        last_choice: dict = {}
        scores: list | None = []
        alerts: list[SliderValueAlert] | None = []

        if self.ld_response_alert and self.ld_continuous_slider and self.ld_response_alert_message:
            alerts = [
                SliderValueAlert(
                    alert=self.ld_response_alert_message,
                    value=None,
                    min_value=self.ld_response_alert_min_value,
                    max_value=self.ld_response_alert_max_value,
                )
            ]

        if self.slider_option and self.slider_option.choices:
            first_choice = self.slider_option.choices[0]
            last_choice = self.slider_option.choices[-1]

            for choice in self.slider_option.choices:
                scores.append(choice.get("score"))  # type: ignore[union-attr]

                if self.ld_response_alert and not self.ld_continuous_slider and choice.get("alert"):
                    alerts.append(  # type: ignore[union-attr]
                        SliderValueAlert(
                            alert=choice.get("alert"),
                            value=choice.get("value"),
                            min_value=None,
                            max_value=None,
                        )
                    )

            if scores and scores[0] is None:
                scores = None

        min = int(first_choice.get("value") or 0)
        max = int(last_choice.get("value") or 1)
        # fmt: off
        response_values = SliderValues(
            min_value=min,
            max_value=max if max > min else max + 1,
            min_label=self.slider_option.ld_min_value or first_choice.get("name"),  # noqa: E501
            max_label=self.slider_option.ld_max_value or last_choice.get("name"),  # noqa: E501
            min_image=first_choice.get("image") or self.slider_option.ld_min_value_img,  # noqa: E501
            max_image=last_choice.get("image") or self.slider_option.ld_max_value_img,  # noqa: E501
            scores=scores,
            alerts=alerts or None,
        )
        # fmt: on

        return response_values

    def resolve_condition(self, condition: ConditionData) -> AnyCondition:
        return ConditionValueResolver().resolve(self.name, condition)


class ReproFieldSliderStacked(ReproFieldSliderBase):
    INPUT_TYPE = "stackedSlider"
    RESPONSE_TYPE = ResponseType.SLIDERROWS

    slider_options: list[LdSliderOption] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)

        ld_slider_options = self.attr_processor.get_attr_list(options_doc, "reproschema:sliderOptions") or []
        self.slider_options = [self._get_slider_option(opt) for opt in ld_slider_options]

    def _build_config(self, _cls: Type | None, **attrs):
        config = SliderRowsConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            timer=int(self.ld_timer / 1000) if self.ld_timer else None,
        )
        return config

    def _build_response_values(self) -> SliderRowsValues | None:
        rows = []
        for option in self.slider_options or []:
            first_choice: dict = {}
            last_choice: dict = {}
            scores: list | None = []
            alerts: list[SliderValueAlert] | None = []

            if option.choices:
                first_choice = option.choices[0]
                last_choice = option.choices[-1]
                for choice in option.choices:
                    scores.append(choice.get("score"))  # type: ignore[union-attr]  # noqa: E501
                    if self.ld_response_alert and choice.get("alert"):
                        alerts.append(  # type: ignore[union-attr]
                            SliderValueAlert(
                                alert=choice.get("alert"),
                                value=choice.get("value"),
                                min_value=None,
                                max_value=None,
                            )
                        )
            if (scores and scores[0] is None) or (scores and None in scores):
                scores = []

            response_value = SliderRowsValue(
                label=option.ld_label,
                min_value=first_choice.get("value"),
                max_value=last_choice.get("value"),
                min_label=option.ld_min_value or first_choice.get("name"),
                max_label=option.ld_max_value or last_choice.get("name"),
                min_image=option.ld_min_value_img or first_choice.get("image"),
                max_image=option.ld_max_value_img or last_choice.get("image"),
                scores=scores,
                alerts=alerts or None,
            )
            rows.append(response_value)

        response_values = SliderRowsValues(rows=rows)

        return response_values


class ReproFieldPhoto(ReproFieldBase):
    INPUT_TYPE = "photo"
    RESPONSE_TYPE = ResponseType.PHOTO
    CFG_TYPE = PhotoConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldVideo(ReproFieldBase):
    INPUT_TYPE = "video"
    RESPONSE_TYPE = ResponseType.VIDEO
    CFG_TYPE = VideoConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldAudio(ReproFieldBase):
    RESPONSE_TYPE = ResponseType.AUDIO
    CFG_TYPE = AudioConfig

    ld_max_duration: int | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return ["audioRecord", "audioImageRecord"]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_max_duration = self.attr_processor.get_translation(
            options_doc, "schema:maxValue", lang=self.lang, drop=drop
        )
        self.ld_option_image = self._get_ld_image(options_doc, drop=drop)

    def _build_response_values(self) -> AudioValues | None:
        max_duration = 300
        if self.ld_max_duration is not None:
            max_duration = int(int(self.ld_max_duration) / 1000)  # seconds
        return AudioValues(max_duration=max_duration)

    def export(self) -> ActivityItemCreate:
        if self.ld_option_image and self.ld_question:
            question = {}
            for lang, val in copy(list(self.ld_question.items())):
                question[lang] = "\r\n\r\n".join([val, self._wrap_wysiwyg_img(self.ld_option_image)])
            self.ld_question = question

        return super().export()


class ReproFieldDrawing(ReproFieldBase):
    INPUT_TYPE = "drawing"
    RESPONSE_TYPE = ResponseType.DRAWING
    CFG_TYPE = DrawingConfig

    ld_remove_undo_option: bool = False
    ld_top_navigation_option: bool = False

    options_image: str | None = None
    background_image: str | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)

        input_options = self.attr_processor.get_attr_list(processed_doc, "reproschema:inputs") or []
        if input_options:
            for obj in input_options:
                name = self.attr_processor.get_translation(obj, "schema:name", self.lang)
                if name == "backgroundImage":
                    self.background_image = self._get_choice_value(obj)
                    break

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_remove_undo_option = self.attr_processor.get_attr_value(options_doc, "reproschema:removeUndoOption")
        self.ld_top_navigation_option = self.attr_processor.get_attr_value(
            options_doc, "reproschema:topNavigationOption"
        )
        self.options_image = self._get_ld_image(options_doc)

    def _build_config(self, _cls: Type | None, **attrs):
        attrs = dict(
            remove_undo_button=bool(self.ld_remove_undo_option),
            navigation_to_top=bool(self.ld_top_navigation_option),
        )
        return super()._build_config(_cls, **attrs)

    def _build_response_values(self) -> DrawingValues | None:
        return DrawingValues(
            drawing_example=self.options_image,
            drawing_background=self.background_image,
        )


class ReproFieldMessage(ReproFieldBase):
    INPUT_TYPE = "markdownMessage"
    INPUT_TYPE_ALT = "markdown-message"
    RESPONSE_TYPE = ResponseType.MESSAGE

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE, cls.INPUT_TYPE_ALT]

    def _build_config(self, _cls: Type | None, **attrs):
        config = MessageConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            timer=int(self.ld_timer / 1000) if self.ld_timer else None,
        )

        return config


class ReproFieldTimeRange(ReproFieldBase):
    INPUT_TYPE = "timeRange"
    RESPONSE_TYPE = ResponseType.TIMERANGE
    CFG_TYPE = TimeRangeConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldDate(ReproFieldBase):
    INPUT_TYPE = "date"
    RESPONSE_TYPE = ResponseType.DATE
    CFG_TYPE = DateConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldTime(ReproFieldBase):
    INPUT_TYPE = "time"
    RESPONSE_TYPE = ResponseType.TIME
    CFG_TYPE = TimeConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldGeolocation(ReproFieldBase):
    INPUT_TYPE = "geolocation"
    RESPONSE_TYPE = ResponseType.GEOLOCATION
    CFG_TYPE = GeolocationConfig

    ld_geolocation_image: str | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)

        self.ld_geolocation_image = self._get_ld_image(options_doc, drop=drop)

    def export(self) -> ActivityItemCreate:
        if self.ld_geolocation_image and self.ld_question:
            question = {}
            for lang, val in copy(list(self.ld_question.items())):
                question[lang] = "\r\n\r\n".join([val, self._wrap_wysiwyg_img(self.ld_geolocation_image)])
            self.ld_question = question

        return super().export()


class ReproFieldAge(ReproFieldBase):
    INPUT_TYPE = "ageSelector"
    RESPONSE_TYPE = ResponseType.NUMBERSELECT
    CFG_TYPE = NumberSelectionConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_min_age = self.attr_processor.get_attr_value(options_doc, "schema:minAge")
        self.ld_max_age = self.attr_processor.get_attr_value(options_doc, "schema:maxAge")

    def _build_config(self, _cls: Type | None, **attrs):
        assert _cls is not None
        if self.ld_is_optional_text:
            additional_response_option = AdditionalResponseOption(
                text_input_option=True,
                text_input_required=bool(self.ld_is_optional_text_required),
            )
        else:
            additional_response_option = AdditionalResponseOption(
                text_input_option=False,
                text_input_required=False,
            )

        config = _cls(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            additional_response_option=additional_response_option,
        )

        return config

    def _build_response_values(self) -> NumberSelectionValues | None:
        return NumberSelectionValues(min_value=self.ld_min_age, max_value=self.ld_max_age)


class ReproFieldAudioStimulus(ReproFieldBase):
    INPUT_TYPE = "audioStimulus"
    RESPONSE_TYPE = ResponseType.AUDIOPLAYER

    LD_OPT_STIMULUS = "stimulus"
    LD_OPT_ALLOW_REPLAY = "allowReplay"

    allow_replay: bool = False
    audio_file: str | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        input_options = self.attr_processor.get_attr_list(processed_doc, "reproschema:inputs")
        if input_options:
            for option in input_options:
                name = self.attr_processor.get_translation(option, "schema:name", self.lang)
                val = self._get_choice_value(option)
                if name == self.LD_OPT_STIMULUS:
                    self.audio_file = val
                elif name == self.LD_OPT_ALLOW_REPLAY:
                    self.allow_replay = val

    def _build_config(self, _cls: Type | None, **attrs):
        if self.ld_is_optional_text:
            additional_response_option = AdditionalResponseOption(
                text_input_option=True,
                text_input_required=bool(self.ld_is_optional_text_required),
            )
        else:
            additional_response_option = AdditionalResponseOption(
                text_input_option=False,
                text_input_required=False,
            )

        config = AudioPlayerConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            additional_response_option=additional_response_option,
            play_once=self.allow_replay is False,
        )

        return config

    def _build_response_values(self) -> AudioPlayerValues | None:
        return AudioPlayerValues(
            file=self.audio_file,
        )


class ReproFieldABTrailIpad(ReproFieldBase, OrderAware):
    INPUT_TYPE = "trail"
    RESPONSE_TYPE = ResponseType.ABTRAILS
    DEVICE_TYPE = ABTrailsDeviceType.TABLET

    ld_description: str | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        self.ld_description = self.attr_processor.get_translation(  # TODO move to extra
            processed_doc, "schema:description", self.lang
        )

    def _get_order_name(self, order: int):
        orders = [
            ABTrailsOrder.FIRST,
            ABTrailsOrder.SECOND,
            ABTrailsOrder.THIRD,
            ABTrailsOrder.FOURTH,
        ]
        try:
            return orders[order]
        except IndexError:
            raise NotImplementedError("Too many trails. Only 4 items supported")

    def _build_config(self, _cls: Type | None, **attrs):
        assert self.order is not None
        config = ABTrailsConfig(
            device_type=self.DEVICE_TYPE,
            order_name=self._get_order_name(self.order),
        )
        return config


class ReproFieldABTrailMobile(ReproFieldABTrailIpad):
    DEVICE_TYPE = ABTrailsDeviceType.MOBILE


class ReproFieldStabilityTracker(ReproFieldBase):
    INPUT_TYPE = "stabilityTracker"
    RESPONSE_TYPE = ResponseType.STABILITYTRACKER

    input_options: dict | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        input_options = self.attr_processor.get_attr_list(processed_doc, "reproschema:inputs") or []
        self.input_options = {}
        if input_options:
            for obj in input_options:
                name = self.attr_processor.get_translation(obj, "schema:name", self.lang)
                val = self._get_choice_value(obj)
                self.input_options[name] = val

    def _build_config(self, _cls: Type | None, **attrs):
        assert self.input_options is not None
        attr_map = {
            "maxOffTargetTime": "max_off_target_time",
            "numTestTrials": "num_test_trials",
            "taskMode": "task_mode",
            "trackingDims": "tracking_dims",
            "showScore": "show_score",
            "lambdaSlope": "lambda_slope",
            "basisFunc": "basis_func",
            "noiseLevel": "noise_level",
            "taskLoopRate": "task_loop_rate",
            "cyclesPerMin": "cycles_per_min",
            "durationMins": "duration_minutes",
            "trialNumber": "trials_number",
            "oobDuration": "oob_duration",
            "initialLambda": "initial_lambda",
            "showPreview": "show_preview",
            "numPreviewStim": "num_preview_stim",
            "previewStepGap": "preview_step_gap",
            "dimensionCount": "dimension_count",
            "maxRad": "max_rad",
        }
        params = {
            param: self.input_options.get(name)
            for name, param in attr_map.items()
            if self.input_options.get(name) is not None
        }
        phase_type = self.input_options["phaseType"]
        phase = Phase.PRACTICE if phase_type == "challenge-phase" else Phase.TEST
        config = StabilityTrackerConfig(
            user_input_type=InputType(self.input_options["userInputType"]),
            phase=phase,
            **params,
        )

        return config


class ReproFieldVisualStimulusResponse(ReproFieldBase):
    INPUT_TYPE = "visual-stimulus-response"
    RESPONSE_TYPE = ResponseType.FLANKER

    input_options: dict | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    def _get_trials(self, doc: dict) -> list[StimulusConfiguration]:
        vals = []

        if obj_list := self.attr_processor.get_attr_list(doc, "schema:itemListElement"):
            for obj in obj_list:
                vals.append(
                    StimulusConfiguration(
                        id=obj.get(LdKeyword.id),
                        image=self._get_ld_image(obj),
                        text=self.attr_processor.get_translation(obj, "schema:name", self.lang),
                        value=self._get_choice_value(obj),
                        # weight: int | None = None  # TODO
                    )
                )

        return vals

    def _get_blocks(self, doc: dict):
        vals = []

        if obj_list := self.attr_processor.get_attr_list(doc, "schema:itemListElement"):
            for obj in obj_list:
                ld_order = self.attr_processor.get_attr_list(obj, "reproschema:order")
                order = [v[LdKeyword.id] for v in ld_order or []]
                vals.append(
                    BlockConfiguration(
                        name=self.attr_processor.get_translation(obj, "schema:name", self.lang),
                        order=order,
                    )
                )

        return vals

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        input_options = self.attr_processor.get_attr_list(processed_doc, "reproschema:inputs") or []
        self.input_options = {}
        if input_options:
            for obj in input_options:
                name = self.attr_processor.get_translation(obj, "schema:name", self.lang)
                val = self._get_choice_value(obj)
                if name == "trials":
                    val = self._get_trials(obj)
                elif name == "blocks":
                    val = self._get_blocks(obj)
                elif name == "buttons":
                    choices = self._get_ld_choices_formatted(obj)
                    if not choices:
                        continue
                    val = []
                    for btn in choices:
                        val.append(
                            ButtonConfiguration(
                                text=btn.get("name"),
                                image=btn.get("image"),
                                value=btn.get("value"),
                            )
                        )
                elif name == "fixationScreen":
                    image = self._get_ld_image(obj)
                    if not image and not val:
                        continue
                    val = FixationScreen(value=val, image=image)

                self.input_options[name] = val

    def _build_config(self, _cls: Type | None, **attrs):
        assert self.input_options is not None
        config = FlankerConfig(
            block_type=BlockType(self.input_options["blockType"]),
            stimulus_trials=self.input_options["trials"],
            blocks=self.input_options["blocks"],
            buttons=self.input_options["buttons"],
            next_button=self.input_options.get("nextButton"),
            fixation_duration=self.input_options.get("fixationDuration"),
            fixation_screen=self.input_options.get("fixationScreen"),
            minimum_accuracy=self.input_options.get("minimumAccuracy"),
            sample_size=self.input_options.get("sampleSize", 1),
            sampling_method=SamplingMethod(self.input_options["samplingMethod"]),
            show_feedback=self.input_options["showFeedback"],
            show_fixation=self.input_options["showFixation"],
            show_results=self.input_options["showResults"],
            trial_duration=self.input_options["trialDuration"],
            is_last_practice=bool(self.input_options.get("lastPractice")),
            is_last_test=bool(self.input_options.get("lastTest")),
            is_first_practice=False,  # TODO ????
            # maxRetryCount  # TODO missed
            # blockIndex  # TODO missed
        )

        return config
