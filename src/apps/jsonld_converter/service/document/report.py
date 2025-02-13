import re
from abc import ABC, abstractmethod
from copy import deepcopy

from apps.activities.domain.conditions import AnyCondition
from apps.activities.domain.scores_reports import CalculationType, Score, Section
from apps.jsonld_converter.errors import ConditionalLogicError
from apps.jsonld_converter.service.document.base import CommonFieldsMixin, LdDocumentBase, LdKeyword
from apps.jsonld_converter.service.document.conditional_logic import (
    ConditionBoolResolver,
    ConditionData,
    ConditionValueResolver,
    ResolvesConditionalLogic,
)


class ReportBase(LdDocumentBase, CommonFieldsMixin, ABC):
    """
    Reports format is broken and doesn't meet ReproSchema and json-ld
    principles. Parsing logic is implemented in order to extract required data
    from broken json-ld document.
    Requires rework.
    """

    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_message: str | None = None

    print_items: list[str] | None = None
    extra: dict | None = None

    @classmethod
    @abstractmethod
    def get_data_type(cls): ...

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            "dataType",
            *cls.attr_processor.resolve_key("schema:DataType"),
        ]
        for ld_type in ld_types:
            if attr := doc.get(ld_type):
                val = cls.attr_processor.first(attr)
                # value is @id here [???]
                if _id := val.get(LdKeyword.id):
                    parts = _id.rsplit("/", 1)[-1].rsplit(":", 1)
                    if parts[-1] == cls.get_data_type():
                        return True
        return False

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        await self._load_from_processed_doc(processed_doc, base_url)

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        assert self.ld_id
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_message = self.attr_processor.get_translation(processed_doc, "reproschema:message", self.lang)
        self.print_items = self._get_print_items(processed_doc)
        self.ld_variable_name = self.attr_processor.extract_compact_id(self.ld_id)

    def _get_print_items(self, doc: dict, *, drop=False) -> list[str]:
        if items := self.attr_processor.get_attr_list(doc, "reproschema:printItems", drop=drop):
            """
            Extract item names [???]
            """
            return [item.get(LdKeyword.value) for item in items if LdKeyword.value in item]
        return []


class ConditionalItem(ResolvesConditionalLogic):
    def __init__(
        self,
        ld_id: str,
        ld_pref_label: str | None,
        ld_alt_label: str | None,
        ld_message: str | None,
        ld_flag_score: bool,
        ld_is_vis: str | bool | None,
        ld_print_items: list[str] | None,
    ):
        self.ld_id = ld_id
        self.ld_pref_label = ld_pref_label
        self.ld_alt_label = ld_alt_label
        self.ld_message = ld_message
        self.ld_flag_score = ld_flag_score
        self.ld_is_vis = ld_is_vis
        self.ld_print_items = ld_print_items
        self.ld_variable_name = ld_id

    def resolve_condition_name(self):
        return self.ld_variable_name

    def resolve_condition(self, condition: ConditionData) -> AnyCondition:
        name = self.resolve_condition_name()
        try:
            return ConditionBoolResolver().resolve(name, condition)
        except NotImplementedError:
            return ConditionValueResolver().resolve(name, condition)


class ReproActivityScore(ReportBase, ResolvesConditionalLogic):
    ld_output_type: str | None = None
    ld_js_expression: str | None = None
    conditionals: list[ConditionalItem] | None = None

    @classmethod
    def get_data_type(cls):
        return "score"

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        self.ld_output_type = self.attr_processor.get_attr_value(processed_doc, "reproschema:outputType")
        self.ld_js_expression = self.attr_processor.get_attr_value(processed_doc, "reproschema:jsExpression")
        self.conditionals = self._get_conditionals(processed_doc)

    def _get_conditionals(self, doc: dict, *, drop=False) -> list[ConditionalItem]:
        conditionals = []
        if items := self.attr_processor.get_attr_list(doc, "reproschema:conditionals", drop=drop):
            for item in items:
                ld_expanded_id = self.attr_processor.first(item.get(LdKeyword.id))
                conditionals.append(
                    ConditionalItem(
                        ld_id=self.attr_processor.extract_compact_id(ld_expanded_id),
                        ld_flag_score=self.attr_processor.get_attr_value(item, "reproschema:flagScore"),
                        ld_is_vis=self._is_visible(item),
                        ld_message=self.attr_processor.get_translation(item, "reproschema:message", self.lang),
                        ld_pref_label=self._get_ld_pref_label(item),
                        ld_alt_label=self._get_ld_alt_label(item),
                        ld_print_items=self._get_print_items(item),
                    )
                )

        return conditionals

    @classmethod
    def _get_score_items(cls, expression: str | None) -> list[str]:
        if not expression:
            return []

        pattern = r"[a-z0-9A-Z][\w\_\+\s]*"
        if not re.match(pattern, expression):
            raise ConditionalLogicError(expression)
        parts = expression.split("+")

        return [v.strip() for v in parts]

    @property
    def calculation_type(self) -> CalculationType:
        assert self.ld_output_type
        if self.ld_output_type == "cumulative":
            return CalculationType.SUM
        return CalculationType(self.ld_output_type)

    def resolve_condition_name(self):
        return self.ld_variable_name

    def resolve_condition(self, condition: ConditionData) -> AnyCondition:
        return ConditionValueResolver().resolve(self.resolve_condition_name(), condition)

    def export(self) -> Score:
        assert self.ld_id
        return Score(
            id=self.attr_processor.extract_compact_id(self.ld_id),
            name=self.ld_alt_label or self.ld_pref_label,
            calculation_type=self.calculation_type,
            items_score=self._get_score_items(self.ld_js_expression),
            message=self.ld_message,
            items_print=self.print_items,
            # conditional logic is populated in activity
        )


class ReproActivitySection(ReportBase):
    ld_is_vis: str | bool | None = None

    @classmethod
    def get_data_type(cls):
        return "section"

    async def _load_from_processed_doc(self, processed_doc: dict, base_url: str | None = None):
        await super()._load_from_processed_doc(processed_doc, base_url)
        self.ld_is_vis = self._is_visible(processed_doc, drop=True)

    def export(self) -> Section:
        return Section(
            name=self.ld_alt_label or self.ld_pref_label,
            message=self.ld_message,
            items_print=self.print_items,
            # conditional logic is populated in activity
        )
