import asyncio
from copy import deepcopy
from typing import Type
from uuid import uuid4

from apps.activities.domain.activity_create import (
    ActivityCreate,
    ActivityItemCreate,
)
from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.scores_reports import (
    Score,
    ScoreConditionalLogic,
    ScoresAndReports,
    Section,
    SectionConditionalLogic,
)
from apps.jsonld_converter.errors import (
    ConditionalLogicError,
    JsonLDNotSupportedError,
)
from apps.jsonld_converter.service.document.base import (
    CommonFieldsMixin,
    ContainsNestedMixin,
    LdDocumentBase,
    LdKeyword,
)
from apps.jsonld_converter.service.document.conditional_logic import (
    ConditionalLogicParser,
    ResolvesConditionalLogic,
)
from apps.jsonld_converter.service.document.field import (  # ReproFieldABTrailIpad,; ReproFieldABTrailMobile,
    ReproFieldAge,
    ReproFieldAudio,
    ReproFieldAudioStimulus,
    ReproFieldBase,
    ReproFieldDate,
    ReproFieldDrawing,
    ReproFieldGeolocation,
    ReproFieldMessage,
    ReproFieldPhoto,
    ReproFieldRadio,
    ReproFieldRadioStacked,
    ReproFieldSlider,
    ReproFieldSliderStacked,
    ReproFieldText,
    ReproFieldTime,
    ReproFieldTimeRange,
    ReproFieldVideo,
)
from apps.jsonld_converter.service.document.report import (
    ReproActivityScore,
    ReproActivitySection,
)


class ReproActivity(LdDocumentBase, ContainsNestedMixin, CommonFieldsMixin):
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_description: dict[str, str] | None = None
    ld_about: dict[str, str] | None = None
    ld_schema_version: str | None = None
    ld_version: str | None = None
    ld_image: str | None = None
    ld_splash: str | None = None
    ld_is_vis: str | bool | None = None
    ld_is_reviewer: bool | None = None
    ld_is_one_page: bool | None = None

    properties: dict
    nested_by_order: list[LdDocumentBase] | None = None
    reports_by_order: list[LdDocumentBase] | None = None

    extra: dict | None = None
    is_skippable: bool = False
    is_back_disabled: bool = False
    is_export_allowed: bool = False
    is_summary_disabled: bool = False

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            "reproschema:Activity",
            *cls.attr_processor.resolve_key("reproschema:Activity"),
        ]
        return cls.attr_processor.first(
            doc.get(LdKeyword.type)
        ) in ld_types and cls.supports_activity_type(doc)

    @classmethod
    def supports_activity_type(cls, doc: dict) -> bool:
        _type = cls.get_activity_type(doc)
        return not _type or _type == "NORMAL"

    @classmethod
    def get_activity_type(cls, doc: dict) -> str | None:
        _type = cls.attr_processor.get_attr_value(
            doc, "reproschema:activityType"
        )
        if not _type:
            # try fetch from compact
            _type = doc.get("activityType")

        return _type

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [
            ReproFieldText,
            ReproFieldRadio,
            ReproFieldSlider,
            ReproFieldSliderStacked,
            ReproFieldPhoto,
            ReproFieldVideo,
            ReproFieldAudio,
            ReproFieldDrawing,
            ReproFieldMessage,
            ReproFieldTimeRange,
            ReproFieldDate,
            ReproFieldTime,
            ReproFieldGeolocation,
            ReproFieldAge,
            ReproFieldRadioStacked,
            ReproFieldAudioStimulus,
            ReproActivityScore,
            ReproActivitySection,
        ]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc: dict = deepcopy(self.doc_expanded)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_description = self._get_ld_description(
            processed_doc, drop=True
        )
        self.ld_about = self._get_ld_about(processed_doc, drop=True)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self.ld_splash = self.attr_processor.get_translation(
            processed_doc, "schema:splash", lang=self.lang, drop=True
        )
        self.ld_is_vis = self._is_visible(processed_doc, drop=True)
        self.ld_is_reviewer = self.attr_processor.get_attr_value(
            processed_doc, "reproschema:isReviewerActivity"
        )
        self.ld_is_one_page = self.attr_processor.get_attr_value(
            processed_doc, "reproschema:isOnePageAssessment"
        )

        allow_list = self._get_allow_list(processed_doc)
        self.is_skippable = self._is_skippable(allow_list)
        self.is_back_disabled = self._is_back_disabled(allow_list)
        self.is_export_allowed = self._is_export_allowed(allow_list)
        self.is_summary_disabled = self._is_summary_disabled(allow_list)

        self.properties = self._get_ld_properties_formatted(processed_doc)
        self.nested_by_order = await self._get_nested_items(processed_doc)
        self.reports_by_order = await self._get_nested_items(
            processed_doc,
            attr_container="reproschema:reports",
            skip_not_supported=False,
        )

        self._load_extra(processed_doc)

    async def _get_nested_items(
        self,
        doc: dict,
        drop=False,
        attr_container="reproschema:order",
        *,
        skip_not_supported=True,
    ) -> list:
        nested_items: list = []
        if items := self.attr_processor.get_attr_list(
            doc, attr_container, drop=drop
        ):
            nested = await asyncio.gather(
                *[
                    self._load_nested_doc(
                        item, skip_not_supported=skip_not_supported
                    )
                    for item in items
                ],
                return_exceptions=True,
            )
            nested_items = []
            for node in nested:
                if isinstance(node, Exception):
                    raise node
                if node:
                    nested_items.append(node)

        return nested_items

    async def _load_nested_doc(self, doc: dict, *, skip_not_supported=True):
        try:
            node = await self.load_supported_document(
                doc, self.base_url, settings=self.settings
            )
            # override from properties
            if node.ld_id in self.properties:
                for prop, val in self.properties[node.ld_id].items():
                    if val is not None and hasattr(node, prop):
                        setattr(node, prop, val)
            return node
        except JsonLDNotSupportedError:
            if skip_not_supported:
                return None
            raise

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def _export_items(self) -> list[ActivityItemCreate]:
        var_item_map = {
            item.ld_variable_name: item
            for item in self.nested_by_order or []
            if isinstance(item, ReproFieldBase)
        }
        models = []
        for item in var_item_map.values():
            model: ActivityItemCreate = item.export()

            expression = item.ld_is_vis
            if isinstance(expression, str):
                try:
                    match, conditions = ConditionalLogicParser(
                        expression
                    ).parse()
                    resolved_conditions = []
                    for condition in conditions:
                        condition_item: ReproFieldBase = var_item_map.get(  # type: ignore # noqa: E501
                            condition.var_name
                        )
                        if condition_item is None:
                            raise ConditionalLogicError(expression)
                        resolved_conditions.append(
                            condition_item.resolve_condition(condition)
                        )
                    model.conditional_logic = ConditionalLogic(
                        match=match, conditions=resolved_conditions
                    )

                except ConditionalLogicError:
                    ...  # TODO
                    raise

            models.append(model)

        return models

    def _resolve_item_names_by_vars(
        self,
        var_item_map: dict[str, ResolvesConditionalLogic],
        vars: list[str],
    ) -> list[str]:
        """
        Resolve item conditional names by variables
        """
        names = []
        for var_name in vars:
            _item = var_item_map.get(var_name)
            if _item is None:
                raise ConditionalLogicError(var_name)
            names.append(_item.resolve_condition_name())

        return names

    def _export_sections(
        self,
        var_item_map: dict[str, ResolvesConditionalLogic],
        items: list[ReproActivitySection],
    ) -> list[Section]:
        models = []
        for item in items:
            model = item.export()
            expression = item.ld_is_vis
            if isinstance(expression, str):
                try:
                    # resolve conditional logic expression with condition name
                    # and condition value
                    match, conditions = ConditionalLogicParser(
                        expression
                    ).parse()
                    resolved_conditions = []
                    for condition in conditions:
                        condition_item: ResolvesConditionalLogic = var_item_map.get(  # type: ignore # noqa: E501
                            condition.var_name
                        )
                        if condition_item is None:
                            raise ConditionalLogicError(expression)
                        resolved_conditions.append(
                            condition_item.resolve_condition(condition)
                        )
                    model.conditional_logic = SectionConditionalLogic(
                        match=match, conditions=resolved_conditions
                    )

                    # replace variables with names
                    if model.items_print:
                        model.items_print = self._resolve_item_names_by_vars(
                            var_item_map, model.items_print
                        )

                except ConditionalLogicError:
                    raise  # TODO

            models.append(model)

        return models

    def _export_scores(
        self,
        var_item_map: dict[str, ResolvesConditionalLogic],
        items: list[ReproActivityScore],
    ) -> list[Score]:
        models = []
        for score in items:
            model = score.export()
            conditionals = []
            for item in score.conditionals or []:
                expression = item.ld_is_vis
                if isinstance(expression, str):
                    try:
                        # resolve conditional logic expression with condition
                        # name and condition value
                        match, conditions = ConditionalLogicParser(
                            expression
                        ).parse()
                        resolved_conditions = []
                        for condition in conditions:
                            condition_item: ResolvesConditionalLogic = var_item_map.get(  # type: ignore # noqa: E501
                                condition.var_name
                            )
                            if condition_item is None:
                                raise ConditionalLogicError(expression)
                            resolved_conditions.append(
                                condition_item.resolve_condition(condition)
                            )

                        conditional_model = ScoreConditionalLogic(
                            name=item.ld_pref_label or item.ld_alt_label,
                            id=item.ld_id,
                            flag_score=bool(item.ld_flag_score),
                            message=item.ld_message or None,
                            items_print=self._resolve_item_names_by_vars(
                                var_item_map, item.ld_print_items or []
                            ),
                            match=match,
                            conditions=resolved_conditions,
                        )
                        conditionals.append(conditional_model)

                    except ConditionalLogicError:
                        raise  # TODO

            model.conditional_logic = conditionals
            if model.items_print:
                model.items_print = self._resolve_item_names_by_vars(
                    var_item_map, model.items_print
                )
            if model.items_score:
                model.items_score = self._resolve_item_names_by_vars(
                    var_item_map, model.items_score
                )
            models.append(model)

        return models

    def _export_reports(self) -> dict:
        var_item_map = {
            item.ld_variable_name: item
            for item in self.nested_by_order or []
            if isinstance(item, ResolvesConditionalLogic)
        }
        sections, scores = [], []
        for item in self.reports_by_order or []:
            if isinstance(item, ReproActivityScore):
                var_item_map[item.ld_variable_name] = item  # type: ignore[assignment] # noqa: E501
                if conditionals := item.conditionals:
                    for conditional in conditionals:
                        var_item_map[conditional.ld_id] = conditional  # type: ignore[assignment] # noqa: E501
                scores.append(item)
            elif isinstance(item, ReproActivitySection):
                var_item_map[item.ld_variable_name] = item  # type: ignore[assignment] # noqa: E501
                sections.append(item)
            else:
                NotImplementedError("Item not supported", item)

        return dict(
            sections=self._export_sections(var_item_map, sections),  # type: ignore[arg-type] # noqa: E501
            scores=self._export_scores(var_item_map, scores),  # type: ignore[arg-type] # noqa: E501
        )

    def export(self) -> ActivityCreate:
        items = self._export_items()
        reports = self._export_reports()

        return ActivityCreate(
            key=uuid4(),
            name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            splash_screen=self.ld_splash or "",  # TODO not loaded
            show_all_at_once=bool(self.ld_is_one_page),
            is_skippable=self.is_skippable,
            is_reviewable=bool(self.ld_is_reviewer),
            response_is_editable=(not self.is_back_disabled),
            is_hidden=self.ld_is_vis is False,
            image=self.ld_image or "",
            items=items,
            extra_fields=self.extra,
            scores_and_reports=ScoresAndReports(
                generate_report=self.is_export_allowed,
                show_score_summary=not self.is_summary_disabled,
                **reports,
            ),
        )


# class ABTrailsIpadActivity(ReproActivity):
#     @classmethod
#     def supports_activity_type(cls, doc: dict) -> bool:
#         return cls.get_activity_type(doc) == "TRAILS_IPAD"
#
#     @classmethod
#     def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
#         return [ReproFieldABTrailIpad]
#
#
# class ABTrailsMobileActivity(ReproActivity):
#     @classmethod
#     def supports_activity_type(cls, doc: dict) -> bool:
#         return cls.get_activity_type(doc) == "TRAILS_MOBILE"
#
#     @classmethod
#     def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
#         return [ReproFieldABTrailMobile]
#
#
# class GyroActivity(ReproActivity):
#     @classmethod
#     def supports_activity_type(cls, doc: dict) -> bool:
#         return cls.get_activity_type(doc) == "CST_GYRO"
#
#     @classmethod
#     def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
#         return [ReproFieldABTrailMobile]
