import asyncio
import dataclasses
from abc import (
    abstractmethod,
    ABC,
)
from copy import deepcopy
from typing import Callable

from pydantic.color import Color
from pyld import (
    jsonld,
    ContextResolver,
)

from apps.activities.domain.response_type_config import (
    ResponseType,
    TextConfig,
    SingleSelectionConfig,
    AdditionalResponseOption,
    SliderConfig,
    MultiSelectionConfig,
    SliderRowsConfig,
)
from apps.activities.domain.response_values import (
    SingleSelectionValues,
    _SingleSelectionValue,
    SliderValues,
    SliderRowsValue,
    SliderRowsValues,
)
from apps.jsonld_converter.domain import LdActivityItemCreate
from apps.jsonld_converter.service.document.base import (
    LdDocumentBase,
    CommonFieldsMixin,
    LdKeyword,
)
from apps.shared.domain import InternalModel


class ReproFieldBase(LdDocumentBase, CommonFieldsMixin):

    @classmethod
    @abstractmethod
    def _get_supported_input_types(cls) -> [str]:
        ...

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:Field',
            *cls.attr_processor.resolve_key('reproschema:Field')
        ]
        _type = cls.attr_processor.first(doc.get(LdKeyword.type))
        _input_type = cls.attr_processor.get_attr_value(doc, 'reproschema:inputType')
        if not _input_type:
            # try fetch from compact
            _input_type = doc.get('ui', {}).get('inputType')

        return _type in ld_types and _input_type in cls._get_supported_input_types()

    def _get_ld_question(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, 'schema:question', drop=drop)

    def _get_ld_readonly(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'schema:readonlyValue', drop=drop)

    def _get_ld_is_multiple(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'reproschema:multipleChoice', drop=drop)

    def _get_choice_value(self, doc: dict, drop=False):
        for attr in ['reproschema:value', 'schema:value']:
            if res := self.attr_processor.get_attr_value(doc, attr, drop=drop):
                break

        return res

    def _get_ld_image(self, doc: dict, drop=False):
        for keyword in [LdKeyword.id, LdKeyword.value]:
            if img := self.attr_processor.get_attr_single(doc, 'schema:image', drop=drop, ld_key=keyword):
                break
        return img

    def _get_ld_choices_formatted(self, doc: dict, drop=False) -> list[dict] | None:
        obj_list = self.attr_processor.get_attr_list(doc, 'reproschema:choices', drop=drop)
        if obj_list is None:
            obj_list = self.attr_processor.get_attr_list(doc, 'schema:itemListElement', drop=drop)
        choices = []
        if obj_list:
            for obj in obj_list:
                choice = {
                    'name': self.attr_processor.get_translation(obj, 'schema:name', self.lang),
                    'value': self._get_choice_value(obj),
                    'image': self._get_ld_image(obj),
                    'is_vis': self.attr_processor.get_attr_value(obj, 'reproschema:isVis'),
                    'alert': self.attr_processor.get_translation(obj, 'schema:alert', self.lang),
                    'color': self.attr_processor.get_attr_value(obj, 'schema:color'),
                    'tooltip': self.attr_processor.get_attr_value(obj, 'schema:description'),
                    'score': self.attr_processor.get_attr_value(obj, 'schema:score'),
                }
                choices.append(choice)

        return choices

    async def _get_ld_response_options_doc(self, doc: dict, drop=False):
        term_attr = 'reproschema:responseOptions'
        key = self.attr_processor.get_key(doc, term_attr)
        options_doc = self.attr_processor.get_attr_single(doc, term_attr)
        if len(options_doc) == 1 and LdKeyword.id in options_doc:
            options_id = options_doc[LdKeyword.id]
            processor_options = dict(
                contextResolver=self.context_resolver,
                documentLoader=self.document_loader,
            )
            options_doc = await asyncio.to_thread(jsonld.expand, options_id, processor_options)  # TODO exception

        if drop:
            del doc[key]

        return options_doc

    def _is_skippable(self, allow_list: list):
        keys = ['reproschema:DontKnow', 'reproschema:dont_know_answer']
        for key in keys:
            for rule in allow_list:
                if isinstance(rule, dict):
                    rule = rule.get(LdKeyword.id)

                if self.attr_processor.is_equal_term_val(rule, key):
                    return True
        return False


class ReproFieldText(ReproFieldBase):

    INPUT_TYPE = 'text'

    ld_version: str | None = None
    ld_schema_version: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_image: str | None = None
    ld_question: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None
    ld_correct_answer: str | None = None
    ld_is_response_identifier: bool | None = None
    ld_max_length: int | None = None
    ld_value_type: str | None = None
    ld_remove_back_option: bool | None = None

    is_multiple: bool = False
    choices: list[dict] | None = None

    extra: dict | None = None
    is_skippable: bool = False

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_question = self._get_ld_question(processed_doc, drop=True)
        self.ld_is_vis = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isVis')
        self.ld_correct_answer = self.attr_processor.get_translation(processed_doc, 'schema:correctAnswer', self.lang)

        allow_list = self.attr_processor.get_attr_list(processed_doc, 'reproschema:allow')
        if allow_list:
            self.is_skippable = self._is_skippable(allow_list)

        await self._process_ld_response_options(processed_doc)

        self._load_extra(processed_doc)

    async def _process_ld_response_options(self, doc: dict, drop=False):
        options_doc = await self._get_ld_response_options_doc(doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_is_response_identifier = self.attr_processor.get_attr_value(options_doc, 'reproschema:isResponseIdentifier')
        self.ld_max_length = self.attr_processor.get_attr_value(options_doc, 'reproschema:maxLength')
        self.ld_required_value = self.attr_processor.get_attr_value(options_doc, 'reproschema:requiredValue')
        self.ld_value_type = self.attr_processor.get_attr_single(options_doc, 'reproschema:valueType', ld_key=LdKeyword.id)
        self.ld_remove_back_option = self.attr_processor.get_attr_value(options_doc, 'reproschema:removeBackOption')

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self) -> InternalModel:
        numerical_response_required = False
        if self.ld_value_type and self.attr_processor.is_equal_term_val(self.ld_value_type, 'xsd:integer'):
            numerical_response_required = True

        config = TextConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            max_response_length=self.ld_max_length or None,
            correct_answer_required=self.ld_correct_answer not in [None, ''],
            correct_answer=self.ld_correct_answer or None,
            numerical_response_required=numerical_response_required,
            response_data_identifier=bool(self.ld_is_response_identifier),
            response_required=bool(self.ld_required_value),
        )
        return LdActivityItemCreate(
            question=self.ld_question or {},
            response_type=ResponseType.TEXT,
            # response_values=response_values,  # TODO?
            config=config,
            name=self.ld_pref_label or self.ld_alt_label,
        )


class ReproFieldRadio(ReproFieldBase):

    INPUT_TYPE = 'radio'

    ld_version: str | None = None
    ld_schema_version: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_image: str | None = None
    ld_question: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None
    ld_allow_edit: bool | None = None
    ld_is_optional_text: bool | None = None
    ld_is_optional_text_required: bool | None = None
    ld_timer: int | None = None
    ld_color_palette: bool | None = None
    ld_randomize_options: bool | None = None
    ld_remove_back_option: bool | None = None
    ld_scoring: bool | None = None

    is_multiple: bool = False
    choices: list[str, dict] | None = None

    extra: dict | None = None
    is_skippable: bool = False

    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        super().__init__(context_resolver, document_loader)

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_question = self._get_ld_question(processed_doc, drop=True)
        self.ld_is_vis = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isVis')
        self.ld_allow_edit = self.attr_processor.get_attr_value(processed_doc, 'reproschema:allowEdit')
        self.ld_is_optional_text = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isOptionalText')
        self.ld_timer = self.attr_processor.get_attr_value(processed_doc, 'reproschema:timer')

        allow_list = self.attr_processor.get_attr_list(processed_doc, 'reproschema:allow')
        if allow_list:
            self.is_skippable = self._is_skippable(allow_list)

        await self._process_ld_response_options(processed_doc)

        self._load_extra(processed_doc)

    async def _process_ld_response_options(self, doc: dict, drop=False):
        options_doc = await self._get_ld_response_options_doc(doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_color_palette = self.attr_processor.get_attr_value(options_doc, 'reproschema:colorPalette')
        self.ld_is_optional_text_required = self.attr_processor.get_attr_value(options_doc, 'reproschema:isOptionalTextRequired')
        self.ld_randomize_options = self.attr_processor.get_attr_value(options_doc, 'reproschema:randomizeOptions')
        self.ld_remove_back_option = self.attr_processor.get_attr_value(options_doc, 'reproschema:removeBackOption')
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, 'reproschema:scoring')

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self) -> InternalModel:
        values = []
        for choice in self.choices:
            color = None
            if color_val := choice.get('color'):
                color = Color(color_val)  # TODO process error

            values.append(_SingleSelectionValue(  # TODO where is value???
                text=choice.get('name'),
                image=choice.get('image') or None,
                score=choice.get('score') if bool(self.ld_scoring) else None,
                tooltip=choice.get('tooltip') or None,
                is_hidden=True if choice.get('is_vis') is False else False,
                color=color,
            ))
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

        response_values = SingleSelectionValues(
            options=values
        )
        args = dict(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            randomize_options=bool(self.ld_randomize_options),  # TODO use allow
            timer=self.ld_timer or None,
            add_scores=bool(self.ld_scoring),
            set_alerts=False,
            add_tooltip=False,
            set_palette=bool(self.ld_color_palette),  # TODO
            additional_response_option=additional_response_option
        )
        response_type = ResponseType.SINGLESELECT
        cfg_cls = SingleSelectionConfig
        if self.is_multiple:
            response_type = ResponseType.MULTISELECT
            cfg_cls = MultiSelectionConfig

        config = cfg_cls(**args)

        return LdActivityItemCreate(
            response_type=response_type,
            question=self.ld_question or {},
            response_values=response_values,
            config=config,
            name=self.ld_pref_label or self.ld_alt_label,
        )


@dataclasses.dataclass
class LdSliderOption:
    ld_label: str | None = None
    ld_min_value: str | None = None
    ld_max_value: str | None = None
    ld_min_value_img: str | None = None
    ld_max_value_img: str | None = None
    choices: list[dict] | None = None


class ReproFieldSliderBase(ReproFieldBase, ABC):
    ld_version: str | None = None
    ld_schema_version: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_image: str | None = None
    ld_question: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None
    ld_allow_edit: bool | None = None
    ld_is_optional_text: bool | None = None
    ld_is_optional_text_required: bool | None = None
    ld_timer: int | None = None
    ld_remove_back_option: bool | None = None
    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None
    ld_response_alert_message: str | None = None
    ld_response_alert_min_value: int | None = None
    ld_response_alert_max_value: int | None = None

    is_skippable: bool = False
    extra: dict | None = None

    def _get_slider_option(self, doc: dict) -> LdSliderOption:
        option = LdSliderOption(
            ld_label=self.attr_processor.get_translation(doc, 'schema:sliderLabel', self.lang),
            ld_min_value=self.attr_processor.get_attr_value(doc, 'schema:minValue'),
            ld_max_value=self.attr_processor.get_attr_value(doc, 'schema:maxValue'),
            ld_min_value_img=self.attr_processor.get_attr_value(doc, 'schema:minValueImg'),
            ld_max_value_img=self.attr_processor.get_attr_value(doc, 'schema:maxValueImg'),
            choices=self._get_ld_choices_formatted(doc),
        )
        return option

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):

        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc)
        self.ld_question = self._get_ld_question(processed_doc, drop=True)
        self.ld_is_vis = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isVis')
        self.ld_allow_edit = self.attr_processor.get_attr_value(processed_doc, 'reproschema:allowEdit')

        self.ld_is_optional_text = self.attr_processor.get_attr_value(processed_doc, 'reproschema:isOptionalText')
        self.ld_timer = self.attr_processor.get_attr_value(processed_doc, 'reproschema:timer')

        allow_list = self.attr_processor.get_attr_list(processed_doc, 'reproschema:allow')
        if allow_list:
            self.is_skippable = self._is_skippable(allow_list)

        options_doc = await self._get_ld_response_options_doc(processed_doc)
        await self._process_ld_response_options(options_doc)

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        await self._load_from_processed_doc(processed_doc, base_url)
        self._load_extra(processed_doc)

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        self.ld_is_optional_text_required = self.attr_processor.get_attr_value(options_doc,
                                                                               'reproschema:isOptionalTextRequired')
        self.ld_remove_back_option = self.attr_processor.get_attr_value(options_doc, 'reproschema:removeBackOption')
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, 'reproschema:scoring')

        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, 'reproschema:responseAlert')
        self.ld_response_alert_message = self.attr_processor.get_attr_value(options_doc, 'schema:responseAlertMessage')
        self.ld_response_alert_min_value = self.attr_processor.get_attr_value(options_doc, 'schema:minAlertValue')
        self.ld_response_alert_max_value = self.attr_processor.get_attr_value(options_doc, 'schema:maxAlertValue')

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v


class ReproFieldSlider(ReproFieldSliderBase):

    INPUT_TYPE = 'slider'

    ld_tick_label: bool | None = None
    ld_tick_mark: bool | None = None
    ld_continuous_slider: bool | None = None

    slider_option: LdSliderOption | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop)
        self.slider_option = self._get_slider_option(options_doc)

        self.ld_tick_label = self.attr_processor.get_attr_value(options_doc, 'reproschema:tickLabel')
        self.ld_tick_mark = self.attr_processor.get_attr_value(options_doc, 'reproschema:tickMark')
        self.ld_continuous_slider = self.attr_processor.get_attr_value(options_doc, 'reproschema:continousSlider')

    def export(self) -> InternalModel:
        first_choice = {}
        last_choice = {}
        if self.slider_option.choices:
            first_choice = self.slider_option.choices[0]
            last_choice = self.slider_option.choices[-1]
        scores = [x.get('score') for x in self.slider_option.choices]
        if scores and scores[0] is None:
            scores = None

        response_values = SliderValues(
            min_value=first_choice.get('value'),
            max_value=last_choice.get('value'),
            min_label=self.slider_option.ld_min_value or first_choice.get('name'),
            max_label=self.slider_option.ld_max_value or last_choice.get('name'),
            min_image=self.slider_option.ld_min_value_img or first_choice.get('image'),
            max_image=self.slider_option.ld_max_value_img or last_choice.get('image'),
            scores=scores
        )

        additional_response_option = None
        if self.ld_is_optional_text:
            additional_response_option = AdditionalResponseOption(
                text_input_option=True,
                text_input_required=bool(self.ld_is_optional_text_required),
            )

        config = SliderConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            additional_response_option=additional_response_option,
            show_tick_marks=bool(self.ld_tick_mark),
            show_tick_labels=bool(self.ld_tick_label),
            continuous_slider=bool(self.ld_continuous_slider),
            timer=self.ld_timer or None,
        )
        return LdActivityItemCreate(
            response_type=ResponseType.SLIDER,
            question=self.ld_question or {},
            response_values=response_values,
            config=config,
            name=self.ld_pref_label or self.ld_alt_label,
            extra_fields=self.extra,
        )


class ReproFieldSliderStacked(ReproFieldSliderBase):

    INPUT_TYPE = 'stackedSlider'

    slider_options: list[LdSliderOption] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop)

        ld_slider_options = self.attr_processor.get_attr_list(options_doc, 'reproschema:sliderOptions') or []
        self.slider_options = [self._get_slider_option(opt) for opt in ld_slider_options]

    def export(self) -> InternalModel:
        rows = []
        for option in self.slider_options:
            first_choice = {}
            last_choice = {}
            if option.choices:
                first_choice = option.choices[0]
                last_choice = option.choices[-1]
            scores = [x.get('score') for x in option.choices]
            if scores and scores[0] is None:
                scores = []
            response_value = SliderRowsValue(
                label=option.ld_label,
                min_value=first_choice.get('value'),
                max_value=last_choice.get('value'),
                min_label=option.ld_min_value or first_choice.get('name'),
                max_label=option.ld_max_value or last_choice.get('name'),
                min_image=option.ld_min_value_img or first_choice.get('image'),
                max_image=option.ld_max_value_img or last_choice.get('image'),
                scores=scores
            )
            rows.append(response_value)

        response_values = SliderRowsValues(rows=rows)

        config = SliderRowsConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            timer=self.ld_timer or None,
        )
        return LdActivityItemCreate(
            response_type=ResponseType.SLIDERROWS,
            question=self.ld_question or {},
            response_values=response_values,
            config=config,
            name=self.ld_pref_label or self.ld_alt_label,
            extra_fields=self.extra,
        )
