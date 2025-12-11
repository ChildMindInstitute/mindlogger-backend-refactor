from collections.abc import Iterable

from apps.activities.domain.response_type_config import PerformanceTaskType, ResponseType
from apps.activities.domain.response_values import PhrasalTemplateFieldType, RequestHealthRecordDataOptType
from apps.activities.domain.scores_reports import (
    ReportType,
    Score,
    ScoresAndReports,
    Section,
    SubscaleItemType,
    SubscaleSetting,
)
from apps.activities.errors import (
    IncorrectConditionItemError,
    IncorrectConditionItemIndexError,
    IncorrectConditionLogicItemTypeError,
    IncorrectConditionOptionError,
    IncorrectPhrasalTemplateItemError,
    IncorrectPhrasalTemplateItemIndexError,
    IncorrectPhrasalTemplateItemTypeError,
    IncorrectScoreItemConfigError,
    IncorrectScoreItemError,
    IncorrectScoreItemTypeError,
    IncorrectScorePrintItemError,
    IncorrectScorePrintItemTypeError,
    IncorrectSectionConditionItemError,
    IncorrectSectionPrintItemError,
    IncorrectSectionPrintItemTypeError,
    IncorrectSubscaleInsideSubscaleError,
    IncorrectSubscaleItemError,
    SubscaleDoesNotExist,
    SubscaleInsideSubscaleError,
    SubscaleItemDoesNotExist,
    SubscaleItemScoreError,
    SubscaleItemTypeError,
    SubscaleItemTypeItemDoesNotExist,
    SubscaleNameDoesNotExist,
    SubscaleSettingDoesNotExist,
)


def validate_item_flow(items: list) -> None:
    item_names = [item.name for item in items]
    # conditional logic for item flow
    for index in range(len(items)):
        if items[index].conditional_logic is not None:
            for condition in items[index].conditional_logic.conditions:
                # check if condition item name is in item names
                if condition.item_name not in item_names:
                    raise IncorrectConditionItemError()
                else:
                    # check if condition item order is less than current item order  # noqa: E501
                    condition_item_index = item_names.index(condition.item_name)
                    condition_source_item = items[condition_item_index]
                    item_type = condition_source_item.config.type
                    if condition_item_index > index:
                        raise IncorrectConditionItemIndexError()

                    # check if condition item type is correct
                    if condition_source_item.response_type not in ResponseType.conditional_logic_types():
                        raise IncorrectConditionLogicItemTypeError()

                    # check if condition option ids are correct
                    if item_type in ResponseType.option_based():
                        if item_type in ResponseType.options_mapped_on_value():
                            option_value_attr = "value"
                            selected_option = str(condition.payload.option_value)
                        else:
                            option_value_attr = "id"
                            selected_option = str(condition.payload.option_value)

                        option_values = []
                        for option in condition_source_item.response_values.options:
                            option_value = getattr(option, option_value_attr)
                            option_values.append(str(option_value))

                        if selected_option not in option_values:
                            raise IncorrectConditionOptionError()


def validate_subscale_setting_match_reports(report: Score, subscale_setting: SubscaleSetting):
    report_subscale_linked = report.subscale_name
    subscales = subscale_setting.subscales
    if not subscales:
        raise SubscaleDoesNotExist()

    linked_subscale = next((subscale for subscale in subscales if subscale.name == report_subscale_linked), None)
    if not linked_subscale:
        raise SubscaleNameDoesNotExist()
    elif not linked_subscale.items:
        raise SubscaleItemDoesNotExist()
    else:
        has_non_subscale_items = any(item.type == SubscaleItemType.ITEM for item in linked_subscale.items)
        if not has_non_subscale_items:
            raise SubscaleItemTypeItemDoesNotExist()


def validate_score_and_sections(  # noqa: C901
    items: list, scores_and_reports: ScoresAndReports | None, subscale_setting: SubscaleSetting | None
) -> None:
    item_names = [item.name for item in items]
    if scores_and_reports:
        score_item_ids = []
        score_condition_item_ids = []
        if not hasattr(scores_and_reports, "reports"):
            return

        scores: Iterable[Score] = (r for r in scores_and_reports.reports if r.type == ReportType.score)
        sections: Iterable[Section] = (r for r in scores_and_reports.reports if r.type == ReportType.section)

        for score in scores:
            score_item_ids.append(score.id)
            if score.scoring_type == "score":
                if not subscale_setting:  # report of type score exist then we need a subscale setting
                    raise SubscaleSettingDoesNotExist()
                else:
                    validate_subscale_setting_match_reports(score, subscale_setting)

            # check if all item names are same as values.name
            for item in score.items_score:
                if item not in item_names:
                    raise IncorrectScoreItemError()
                else:
                    score_item_index = item_names.index(item)
                    if items[score_item_index].response_type not in [
                        ResponseType.SINGLESELECT,
                        ResponseType.MULTISELECT,
                        ResponseType.SLIDER,
                    ]:
                        raise IncorrectScoreItemTypeError()
                    if not items[score_item_index].config.add_scores:
                        raise IncorrectScoreItemConfigError()

            print_item_types = [
                ResponseType.SINGLESELECT,
                ResponseType.MULTISELECT,
                ResponseType.SLIDER,
                ResponseType.TEXT,
                ResponseType.PARAGRAPHTEXT,
                ResponseType.NUMBERSELECT,
            ]

            for item in score.items_print:
                if item not in item_names:
                    raise IncorrectScorePrintItemError()
                else:
                    if items[item_names.index(item)].response_type not in print_item_types:
                        raise IncorrectScorePrintItemTypeError()

            if score.conditional_logic:
                for conditional_logic in score.conditional_logic:
                    score_condition_item_ids.append(conditional_logic.id)
                    for item in conditional_logic.items_print:
                        if item not in item_names:
                            raise IncorrectScorePrintItemError()
                        else:
                            if items[item_names.index(item)].response_type not in print_item_types:
                                raise IncorrectScorePrintItemTypeError()

        for section in sections:
            for item in section.items_print:
                if item not in item_names:
                    raise IncorrectSectionPrintItemError()
                else:
                    if items[item_names.index(item)].response_type not in [
                        ResponseType.SINGLESELECT,
                        ResponseType.MULTISELECT,
                        ResponseType.SLIDER,
                        ResponseType.TEXT,
                        ResponseType.PARAGRAPHTEXT,
                    ]:
                        raise IncorrectSectionPrintItemTypeError()

            if section.conditional_logic:
                if hasattr(section.conditional_logic, "conditions"):
                    for condition in section.conditional_logic.conditions:
                        dependency_conditions = (
                            condition.item_name in item_names,
                            condition.item_name in score_item_ids,
                            condition.item_name in score_condition_item_ids,
                        )

                        if not any(dependency_conditions):
                            raise IncorrectSectionConditionItemError()


def validate_subscales(items: list, subscale_setting: SubscaleSetting | None) -> None:
    # validate items inside subscale exist
    # and scores for them are set
    if subscale_setting:
        subscales = subscale_setting.subscales
        item_names = [item.name for item in items]
        subscale_names = [subscale.name for subscale in subscales]
        for subscale in subscales:
            for subscale_item_name in subscale.items:
                if subscale_item_name.type in [
                    SubscaleItemType.ITEM,
                ]:
                    if subscale_item_name.name not in item_names:
                        raise IncorrectSubscaleItemError()
                    subscale_item_index = item_names.index(subscale_item_name.name)

                    if items[subscale_item_index].response_type not in [
                        ResponseType.SINGLESELECT,
                        ResponseType.MULTISELECT,
                        ResponseType.SLIDER,
                    ]:
                        raise SubscaleItemTypeError()

                    if not items[subscale_item_index].config.add_scores:
                        raise SubscaleItemScoreError()
                elif subscale_item_name.type in [
                    SubscaleItemType.SUBSCALE,
                ]:
                    if subscale_item_name.name not in subscale_names:
                        raise IncorrectSubscaleInsideSubscaleError()
                    else:
                        if subscale_item_name.name == subscale.name:
                            raise SubscaleInsideSubscaleError()


def validate_performance_task_type(
    items: list, performance_task_type: PerformanceTaskType | None
) -> PerformanceTaskType | None:
    for item in items:
        if item.response_type == ResponseType.STABILITYTRACKER:
            if item.config.user_input_type in PerformanceTaskType:
                return PerformanceTaskType(item.config.user_input_type)
        elif item.response_type in (
            ResponseType.FLANKER,
            ResponseType.ABTRAILS,
            ResponseType.UNITY,
        ):
            if item.response_type in PerformanceTaskType:
                return PerformanceTaskType(item.response_type)
    return performance_task_type


def validate_phrasal_templates(items: list) -> None:
    for item in items:
        if item.response_type == ResponseType.PHRASAL_TEMPLATE:
            phrases = item.response_values.phrases or []
            for phrase in phrases:
                fields = phrase.fields or []
                for field in fields:
                    if field.type == PhrasalTemplateFieldType.ITEM_RESPONSE:
                        referenced_item = next((item for item in items if item.name == field.item_name), None)
                        if referenced_item is None:
                            raise IncorrectPhrasalTemplateItemError()

                        if referenced_item.response_type not in [
                            ResponseType.DATE,
                            ResponseType.MULTISELECT,
                            ResponseType.MULTISELECTROWS,
                            ResponseType.NUMBERSELECT,
                            ResponseType.SINGLESELECT,
                            ResponseType.SINGLESELECTROWS,
                            ResponseType.SLIDER,
                            ResponseType.SLIDERROWS,
                            ResponseType.TEXT,
                            ResponseType.TIME,
                            ResponseType.TIMERANGE,
                            ResponseType.PARAGRAPHTEXT,
                            ResponseType.MULTISELECTROWS,
                        ]:
                            raise IncorrectPhrasalTemplateItemTypeError()

                        if referenced_item.response_type in [ResponseType.SLIDERROWS] and field.item_index is None:
                            raise IncorrectPhrasalTemplateItemIndexError()


def validate_request_health_record_data(items: list) -> None:
    for item in items:
        if item.response_type == ResponseType.REQUEST_HEALTH_RECORD_DATA:
            if item.response_values.opt_in_out_options is None or len(item.response_values.opt_in_out_options) != 2:
                raise ValueError("Request Health Record Data item must have 2 opt-in/out options")
            opt_in_item = next(
                (
                    option
                    for option in item.response_values.opt_in_out_options
                    if option.id == RequestHealthRecordDataOptType.OPT_IN
                ),
                None,
            )
            if opt_in_item is None:
                raise ValueError("Request Health Record Data item must have opt-in option")
            opt_out_item = next(
                (
                    option
                    for option in item.response_values.opt_in_out_options
                    if option.id == RequestHealthRecordDataOptType.OPT_OUT
                ),
                None,
            )
            if opt_out_item is None:
                raise ValueError("Request Health Record Data item must have opt-out option")
