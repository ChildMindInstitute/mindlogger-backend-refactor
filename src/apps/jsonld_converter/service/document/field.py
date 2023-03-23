import asyncio
from abc import (
    abstractmethod,
)
from copy import deepcopy

from pyld import jsonld

from apps.activities.domain.response_type_config import (
    ResponseType,
    TextConfig,
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

    def _get_ld_choices_formatted(self, doc: dict, drop=False) -> list[str | dict] | None:
        obj_list = self.attr_processor.get_attr_list(doc, 'reproschema:choices', drop=drop)

        choices = []
        if obj_list:
            for obj in obj_list:
                choice = self.attr_processor.get_translation(obj, 'schema:name', self.lang)
                value = self.attr_processor.get_attr_value(obj, 'reproschema:value')
                if value is not None:
                    choice = {'name': choice, 'value': value}
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


class ReproFieldText(ReproFieldBase):

    INPUT_TYPE = 'text'

    ld_version: str | None = None
    ld_schema_version: str | None = None
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_image: str | None = None
    ld_question: dict[str, str] | None = None
    ld_is_vis: str | bool | None = None

    is_multiple: bool = False
    choices: list[str, dict] | None = None

    extra: dict | None = None

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

        await self._process_ld_response_options(processed_doc)

        self._load_extra(processed_doc)

    async def _process_ld_response_options(self, doc: dict, drop=False):
        options_doc = await self._get_ld_response_options_doc(doc, drop=drop)
        self.is_multiple = self._get_ld_is_multiple(options_doc)
        self.choices = self._get_ld_choices_formatted(options_doc)

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self) -> InternalModel:
        answers = self.choices or []
        config = TextConfig(
            max_response_length=-1,
            correct_answer_required=False,
            correct_answer="",
            numerical_response_required=False,
            response_data_identifier="",
            response_required=False,
        )
        return LdActivityItemCreate(
            header_image=self.ld_image or None,
            question=self.ld_question or {},
            response_type=ResponseType.TEXT,
            answers=answers,
            config=config,
            skippable_item=False,
            remove_availability_to_go_back=False,
            extra_fields=self.extra
        )
