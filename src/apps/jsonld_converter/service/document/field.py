import asyncio
import dataclasses
from abc import (
    abstractmethod,
    ABC,
)
from copy import deepcopy
from typing import (
    Callable,
    Type,
)

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
    PhotoConfig,
    ResponseTypeConfig,
    VideoConfig,
    AudioConfig,
    DrawingConfig,
    MessageConfig,
    TimeRangeConfig,
    DateConfig,
    GeolocationConfig,
    NumberSelectionConfig,
    MultiSelectionRowsConfig,
    SingleSelectionRowsConfig,
)
from apps.activities.domain.response_values import (
    SingleSelectionValues,
    _SingleSelectionValue,
    SliderValues,
    SliderRowsValue,
    SliderRowsValues,
    ResponseValueConfig,
    MultiSelectionValues,
    AudioValues,
    DrawingValues,
    NumberSelectionValues,
    MultiSelectionRowsValues,
    SingleSelectionRowsValues,
    _SingleSelectionRowsValue,
    _SingleSelectionRowValue,
)
from apps.jsonld_converter.domain import LdActivityItemCreate
from apps.jsonld_converter.service.document.base import (
    LdDocumentBase,
    CommonFieldsMixin,
    LdKeyword,
)


class ReproFieldBase(LdDocumentBase, CommonFieldsMixin):
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

    def _format_choice(self, doc: dict):
        choice = {
            'name': self.attr_processor.get_translation(doc, 'schema:name', self.lang),
            'value': self._get_choice_value(doc),
            'image': self._get_ld_image(doc),
            'is_vis': self.attr_processor.get_attr_value(doc, 'reproschema:isVis'),
            'alert': self.attr_processor.get_translation(doc, 'schema:alert', self.lang),
            'color': self.attr_processor.get_attr_value(doc, 'schema:color'),
            'tooltip': self.attr_processor.get_attr_value(doc, 'schema:description'),
            'score': self.attr_processor.get_attr_value(doc, 'schema:score'),
        }
        return choice

    def _get_ld_choices_formatted(self, doc: dict, drop=False, keys: list[str] | None = None) -> list[dict] | None:
        keys = keys or ['reproschema:choices', 'schema:itemListElement']
        choices = []

        for key in keys:
            obj_list = self.attr_processor.get_attr_list(doc, key, drop=drop)
            if obj_list:
                break

        if obj_list:
            for obj in obj_list:
                choice = self._format_choice(obj)
                choices.append(choice)

        return choices

    async def _get_ld_response_options_doc(self, doc: dict, drop=False, term_attr: str | None = None):
        term_attr = term_attr or 'reproschema:responseOptions'
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

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
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
        if options_doc:
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

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def _build_config(self, _cls: Type, **attrs):
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
            timer=self.ld_timer or None,
            **attrs
        )

        return config

    def _build_response_values(self) -> ResponseValueConfig | None:
        return None

    def export(self) -> LdActivityItemCreate:
        cfg_cls = self.CFG_TYPE
        config = self._build_config(cfg_cls)
        response_values = self._build_response_values()
        return LdActivityItemCreate(
            question=self.ld_question or {},
            response_type=self.RESPONSE_TYPE,
            response_values=response_values,
            config=config,
            name=self.ld_pref_label or self.ld_alt_label,
            extra_fields=self.extra
        )


class ReproFieldText(ReproFieldBase):

    INPUT_TYPE = 'text'
    RESPONSE_TYPE = ResponseType.TEXT

    ld_correct_answer: str | None = None
    ld_is_response_identifier: bool | None = None
    ld_max_length: int | None = None
    ld_value_type: str | None = None

    is_multiple: bool = False
    choices: list[dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        self.ld_correct_answer = self.attr_processor.get_translation(processed_doc, 'schema:correctAnswer', self.lang)

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_is_response_identifier = self.attr_processor.get_attr_value(options_doc, 'reproschema:isResponseIdentifier')
        self.ld_max_length = self.attr_processor.get_attr_value(options_doc, 'reproschema:maxLength')
        self.ld_required_value = self.attr_processor.get_attr_value(options_doc, 'reproschema:requiredValue')
        self.ld_value_type = self.attr_processor.get_attr_single(options_doc, 'reproschema:valueType', ld_key=LdKeyword.id)

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _build_config(self, _cls: Type, **attrs):
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
        return config


class ReproFieldRadio(ReproFieldBase):

    INPUT_TYPE = 'radio'
    RESPONSE_TYPE = ResponseType.SINGLESELECT

    ld_color_palette: bool | None = None
    ld_randomize_options: bool | None = None
    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None

    is_multiple: bool = False
    choices: list[str, dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_color_palette = self.attr_processor.get_attr_value(options_doc, 'reproschema:colorPalette')
        self.ld_randomize_options = self.attr_processor.get_attr_value(options_doc, 'reproschema:randomizeOptions')
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, 'reproschema:scoring')
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, 'reproschema:responseAlert')

        self.choices = self._get_ld_choices_formatted(options_doc)

    def _build_config(self, _cls: Type, **attrs):
        args = dict(
            randomize_options=bool(self.ld_randomize_options),  # TODO use allow
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            add_tooltip=False,  # TODO
            set_palette=bool(self.ld_color_palette),  # TODO
        )
        cfg_cls = MultiSelectionConfig if self.is_multiple else SingleSelectionConfig

        return super()._build_config(cfg_cls, **args)

    def _build_response_values(self) -> ResponseValueConfig | None:
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
        _cls = MultiSelectionValues if self.is_multiple else SingleSelectionValues
        response_values = _cls(options=values)

        return response_values

    def export(self) -> LdActivityItemCreate:
        if self.is_multiple:
            self.RESPONSE_TYPE = ResponseType.MULTISELECT
        return super().export()


class ReproFieldRadioStacked(ReproFieldBase):

    INPUT_TYPE = 'stackedRadio'
    RESPONSE_TYPE = ResponseType.SINGLESELECTROWS

    ld_scoring: bool | None = None
    ld_response_alert: bool | None = None
    ld_item_list: list[dict] | None = None
    ld_options: list[dict] | None = None
    ld_item_options: list[dict] | None = None

    is_multiple: bool = False
    choices: list[str, dict] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, 'reproschema:scoring')
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, 'reproschema:responseAlert')

        self.ld_item_list = self._get_ld_choices_formatted(options_doc, keys=['reproschema:itemList'])
        self.ld_options = self._get_ld_choices_formatted(options_doc, keys=['reproschema:options'])
        self.ld_item_options = self._get_ld_choices_formatted(options_doc, keys=['reproschema:itemOptions'])

    def _build_config(self, _cls: Type, **attrs):
        cfg_cls = MultiSelectionRowsConfig if self.is_multiple else SingleSelectionRowsConfig

        config = cfg_cls(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            timer=self.ld_timer or None,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            add_tooltip=False,  # TODO
        )

        return config

    def _build_response_values(self) -> ResponseValueConfig | None:
        rows = []
        chunk_size = len(self.ld_options)
        vals = [self.ld_item_options[i:i + chunk_size] for i in range(0, len(self.ld_item_options), chunk_size)]

        for i, item in enumerate(self.ld_item_list or []):
            options = []
            for j, choice in enumerate(self.ld_options or []):
                val = vals[i][j]  # TODO key error
                options.append(_SingleSelectionRowValue(
                    text=choice.get('name'),
                    image=choice.get('image') or None,
                    score=val.get('score') if bool(self.ld_scoring) else None,
                    tooltip=choice.get('tooltip') or None,
                ))

            row = _SingleSelectionRowsValue(
                row_name=item.get('name'),
                row_image=item.get('image') or None,
                tooltip=item.get('tooltip') or None,
                options=options
            )
            rows.append(row)

        _cls = MultiSelectionRowsValues if self.is_multiple else SingleSelectionRowsValues
        response_values = _cls(rows=rows)

        return response_values

    def export(self) -> LdActivityItemCreate:
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
            ld_label=self.attr_processor.get_translation(doc, 'schema:sliderLabel', self.lang),
            ld_min_value=self.attr_processor.get_attr_value(doc, 'schema:minValue'),
            ld_max_value=self.attr_processor.get_attr_value(doc, 'schema:maxValue'),
            ld_min_value_img=self.attr_processor.get_attr_value(doc, 'schema:minValueImg'),
            ld_max_value_img=self.attr_processor.get_attr_value(doc, 'schema:maxValueImg'),
            choices=self._get_ld_choices_formatted(doc),
        )
        return option

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_scoring = self.attr_processor.get_attr_value(options_doc, 'reproschema:scoring')
        self.ld_response_alert = self.attr_processor.get_attr_value(options_doc, 'reproschema:responseAlert')
        self.ld_response_alert_message = self.attr_processor.get_attr_value(options_doc, 'schema:responseAlertMessage')
        self.ld_response_alert_min_value = self.attr_processor.get_attr_value(options_doc, 'schema:minAlertValue')
        self.ld_response_alert_max_value = self.attr_processor.get_attr_value(options_doc, 'schema:maxAlertValue')


class ReproFieldSlider(ReproFieldSliderBase):

    INPUT_TYPE = 'slider'
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

        self.ld_tick_label = self.attr_processor.get_attr_value(options_doc, 'reproschema:tickLabel')
        self.ld_tick_mark = self.attr_processor.get_attr_value(options_doc, 'reproschema:tickMark')
        self.ld_continuous_slider = self.attr_processor.get_attr_value(options_doc, 'reproschema:continousSlider')

    def _build_config(self, _cls: Type, **attrs):
        attrs = dict(
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            show_tick_marks=bool(self.ld_tick_mark),
            show_tick_labels=bool(self.ld_tick_label),
            continuous_slider=bool(self.ld_continuous_slider),
        )
        return super()._build_config(_cls, **attrs)

    def _build_response_values(self) -> ResponseValueConfig | None:
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

        return response_values


class ReproFieldSliderStacked(ReproFieldSliderBase):

    INPUT_TYPE = 'stackedSlider'
    RESPONSE_TYPE = ResponseType.SLIDERROWS

    slider_options: list[LdSliderOption] | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)

        ld_slider_options = self.attr_processor.get_attr_list(options_doc, 'reproschema:sliderOptions') or []
        self.slider_options = [self._get_slider_option(opt) for opt in ld_slider_options]

    def _build_config(self, _cls: Type, **attrs):
        config = SliderRowsConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            skippable_item=self.is_skippable,
            add_scores=bool(self.ld_scoring),
            set_alerts=bool(self.ld_response_alert),
            timer=self.ld_timer or None,
        )
        return config

    def _build_response_values(self) -> SliderRowsValues | None:
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

        return response_values


class ReproFieldPhoto(ReproFieldBase):

    INPUT_TYPE = 'photo'
    RESPONSE_TYPE = ResponseType.PHOTO
    CFG_TYPE = PhotoConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldVideo(ReproFieldBase):

    INPUT_TYPE = 'video'
    RESPONSE_TYPE = ResponseType.VIDEO
    CFG_TYPE = VideoConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldAudio(ReproFieldBase):
    INPUT_TYPE = 'audioRecord'
    RESPONSE_TYPE = ResponseType.AUDIO
    CFG_TYPE = AudioConfig

    ld_max_duration: int | None = None

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_max_duration = self.attr_processor.get_translation(options_doc, 'schema:maxValue', lang=self.lang)

    def _build_response_values(self) -> AudioValues | None:
        return AudioValues(max_duration=self.ld_max_duration or 300)


class ReproFieldDrawing(ReproFieldBase):

    INPUT_TYPE = 'drawing'
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
                name = self.attr_processor.get_translation(obj, 'schema:name', self.lang)
                if name == 'backgroundImage':
                    self.background_image = self._get_choice_value(obj)
                    break

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_remove_undo_option = self.attr_processor.get_attr_value(options_doc, 'reproschema:removeUndoOption')
        self.ld_top_navigation_option = self.attr_processor.get_attr_value(options_doc, 'reproschema:topNavigationOption')
        self.options_image = self._get_ld_image(options_doc)

    def _build_config(self, _cls: Type, **attrs):
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
    INPUT_TYPE = 'markdownMessage'
    RESPONSE_TYPE = ResponseType.MESSAGE

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    def _build_config(self, _cls: Type, **attrs):
        config = MessageConfig(
            remove_back_button=bool(self.ld_remove_back_option),
            timer=self.ld_timer or None,
        )

        return config


class ReproFieldTimeRange(ReproFieldBase):
    INPUT_TYPE = 'timeRange'
    RESPONSE_TYPE = ResponseType.TIMERANGE
    CFG_TYPE = TimeRangeConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldDate(ReproFieldBase):
    INPUT_TYPE = 'date'
    RESPONSE_TYPE = ResponseType.DATE
    CFG_TYPE = DateConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldGeolocation(ReproFieldBase):
    INPUT_TYPE = 'geolocation'
    RESPONSE_TYPE = ResponseType.GEOLOCATION
    CFG_TYPE = GeolocationConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]


class ReproFieldAge(ReproFieldBase):
    INPUT_TYPE = 'ageSelector'
    RESPONSE_TYPE = ResponseType.NUMBERSELECT
    CFG_TYPE = NumberSelectionConfig

    @classmethod
    def _get_supported_input_types(cls) -> list[str]:
        return [cls.INPUT_TYPE]

    async def _process_ld_response_options(self, options_doc: dict, drop=False):
        await super()._process_ld_response_options(options_doc, drop=drop)
        self.ld_min_age = self.attr_processor.get_attr_value(options_doc, 'schema:minAge')
        self.ld_max_age = self.attr_processor.get_attr_value(options_doc, 'schema:maxAge')

    def _build_config(self, _cls: Type, **attrs):
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
        return NumberSelectionValues(
            min_value=self.ld_min_age,
            max_value=self.ld_max_age
        )
