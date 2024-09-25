import copy
from abc import ABC, abstractmethod

from apps.activities.domain.scores_reports import (
    Subscale,
    SubscaleCalculationType,
    SubscaleItem,
    SubscaleItemType,
    SubScaleLookupTable,
    TotalScoreTable,
)
from apps.jsonld_converter.service.document.base import CommonFieldsMixin, LdAttributeProcessor
from apps.jsonld_converter.service.domain import FinalSubscale


class LdSubscaleBase(CommonFieldsMixin, ABC):
    """
    Subscale format is broken and doesn't meet ReproSchema and json-ld
    principles. Parsing logic is implemented in order to extract required data
    from broken json-ld document.
    Requires rework.
    """

    attr_processor: LdAttributeProcessor = LdAttributeProcessor()

    def __init__(self, doc: dict):
        self.doc = copy.deepcopy(doc)
        self.ld_variable_name: str = self.attr_processor.get_attr_value(doc, "reproschema:variableName")
        self.ld_is_average_score: bool = self.attr_processor.get_attr_value(doc, "reproschema:isAverageScore") or False

        ld_lookup_table = self.attr_processor.get_attr_list(doc, "reproschema:lookupTable") or []
        self.lookup_table: list[dict] | None = self._get_lookup_table(ld_lookup_table)

    def _get_lookup_table(self, ld_lookup_table: list[dict]) -> list[dict] | None:
        lookup_table = []
        for doc in ld_lookup_table:
            lookup_table.append(self._get_lookup_table_row(doc))

        return lookup_table

    def _get_lookup_table_row(self, doc: dict) -> dict:
        score = self.attr_processor.get_attr_value(doc, "reproschema:rawScore")
        if score:
            score = score.replace("-", "~")
        return dict(
            raw_score=score,
            output_text=self.attr_processor.get_translation(doc, "reproschema:outputText", self.lang),
        )

    def _export_subscale_calculation_type(self) -> SubscaleCalculationType:
        return SubscaleCalculationType.AVERAGE if self.ld_is_average_score else SubscaleCalculationType.SUM

    @abstractmethod
    def export(self):
        ...


class LdSubscaleFinal(LdSubscaleBase):
    def _export_lookup_table(self):
        score_table_data = []
        if self.lookup_table:
            for item in self.lookup_table:
                if item["raw_score"].startswith("~"):
                    item["raw_score"] = item["raw_score"].replace("~", "", 1)
                score_table_data.append(
                    TotalScoreTable(
                        raw_score=item["raw_score"],  # TODO check strange validation
                        optional_text=item["output_text"] or None,
                    )
                )
        return score_table_data

    def export(self) -> FinalSubscale:
        return FinalSubscale(
            calculate_total_score=self._export_subscale_calculation_type(),
            total_scores_table_data=self._export_lookup_table() or None,
        )


class LdSubscale(LdSubscaleBase):
    def __init__(self, doc):
        super().__init__(doc)
        self.ld_js_expression = self.attr_processor.get_attr_value(doc, "reproschema:jsExpression")

    @classmethod
    def _get_score_items(cls, expression: str | None) -> list[SubscaleItem]:
        if not expression:
            return []

        parts = expression.split("+")
        items = []
        for v in parts:
            v = v.strip()
            type_ = SubscaleItemType.ITEM
            if v[0] == "(" and v[-1] == ")":  # TODO shit logic, move to upper level
                v = v[1:-1]
                type_ = SubscaleItemType.SUBSCALE
            items.append(SubscaleItem(name=v, type=type_))

        return items

    def _get_lookup_table_row(self, doc: dict) -> dict:
        row = super()._get_lookup_table_row(doc)
        row.update(
            age=self.attr_processor.get_attr_value(doc, "reproschema:age") or None,
            sex=self.attr_processor.get_attr_value(doc, "reproschema:sex") or None,
            score=self.attr_processor.get_attr_value(doc, "reproschema:tScore"),
        )
        return row

    def _export_lookup_table(self):
        score_table_data = []
        if self.lookup_table:
            for item in self.lookup_table:
                if isinstance(item["age"], str) and "-" in item["age"]:
                    item["age"] = int(item["age"].split("-")[-1])

                score_table_data.append(
                    SubScaleLookupTable(
                        raw_score=item["raw_score"],  # TODO check strange validation
                        optional_text=item["output_text"],
                        score=item["score"],
                        age=item["age"],
                        sex=item["sex"],
                    )
                )
        return score_table_data

    def export(self) -> Subscale:
        return Subscale(
            name=self.ld_variable_name,
            scoring=self._export_subscale_calculation_type(),
            items=self._get_score_items(self.ld_js_expression),
            subscale_table_data=self._export_lookup_table(),
        )
