from apps.activities.domain.response_type_config import PerformanceTaskType, ResponseType
from apps.activities.domain.response_values import PhrasalTemplateFieldType
from apps.activities.domain.scores_reports import ReportType, Score, SubscaleItemType, SubscaleSetting
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


def validate_item_flow(values: dict):
    items = values.get("items", [])
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

    return values


def validate_subscale_setting_match_reports(report: Score, subscale_setting: SubscaleSetting):
    if not subscale_setting:  # report of type score exist then we need a subscale setting
        raise SubscaleSettingDoesNotExist()
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


def validate_score_and_sections(values: dict):  # noqa: C901
    items = values.get("items", [])
    item_names = [item.name for item in items]
    scores_and_reports = values.get("scores_and_reports")
    if scores_and_reports:
        score_item_ids = []
        score_condition_item_ids = []
        if not hasattr(scores_and_reports, "reports"):
            return

        scores = filter(lambda r: r.type == ReportType.score, scores_and_reports.reports)
        sections = filter(lambda r: r.type == ReportType.section, scores_and_reports.reports)

        for report in list(scores):
            score_item_ids.append(report.id)
            if report.scoring_type == "score":
                subscale_setting = values.get("subscale_setting")
                validate_subscale_setting_match_reports(report, subscale_setting)

            # check if all item names are same as values.name
            for item in report.items_score:
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

            for item in report.items_print:
                if item not in item_names:
                    raise IncorrectScorePrintItemError()
                else:
                    if items[item_names.index(item)].response_type not in [
                        ResponseType.SINGLESELECT,
                        ResponseType.MULTISELECT,
                        ResponseType.SLIDER,
                        ResponseType.TEXT,
                        ResponseType.PARAGRAPHTEXT,
                    ]:
                        raise IncorrectScorePrintItemTypeError()

            if report.conditional_logic:
                for conditional_logic in report.conditional_logic:
                    score_condition_item_ids.append(conditional_logic.id)
                    for item in conditional_logic.items_print:
                        if item not in item_names:
                            raise IncorrectScorePrintItemError()
                        else:
                            if items[item_names.index(item)].response_type not in [
                                ResponseType.SINGLESELECT,
                                ResponseType.MULTISELECT,
                                ResponseType.SLIDER,
                                ResponseType.TEXT,
                                ResponseType.PARAGRAPHTEXT,
                            ]:
                                raise IncorrectScorePrintItemTypeError()

        for report in list(sections):
            for item in report.items_print:
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

            if report.conditional_logic:
                if hasattr(report.conditional_logic, "conditions"):
                    for item in report.conditional_logic.conditions:
                        dependency_conditions = (
                            item.item_name in item_names,
                            item.item_name in score_item_ids,
                            item.item_name in score_condition_item_ids,
                        )

                        if not any(dependency_conditions):
                            raise IncorrectSectionConditionItemError()

    return values


def validate_subscales(values: dict):
    # validate items inside subscale exist
    # and scores for them are set
    subscale_setting = values.get("subscale_setting")
    if subscale_setting:
        subscales = subscale_setting.subscales
        items = values.get("items", [])
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

    return values


def validate_performance_task_type(values: dict):
    # if items type is performance task type or contains part of the name
    # of some performance task, then performance task type must be set
    items = values.get("items", [])
    for item in items:
        if item.response_type == ResponseType.STABILITYTRACKER:
            value = item.dict()["config"]["user_input_type"]
            for v in PerformanceTaskType.get_values():
                if value == v:
                    values["performance_task_type"] = value
        elif item.response_type in (
            ResponseType.FLANKER,
            ResponseType.ABTRAILS,
            ResponseType.UNITY,
        ):
            values["performance_task_type"] = item.response_type
    return values


def validate_phrasal_templates(values: dict):
    items = values.get("items", [])
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
                            ResponseType.TEXT,
                            ResponseType.SINGLESELECT,
                            ResponseType.MULTISELECT,
                            ResponseType.SLIDER,
                            ResponseType.NUMBERSELECT,
                            ResponseType.TIMERANGE,
                            ResponseType.DATE,
                            ResponseType.SLIDERROWS,
                            ResponseType.SINGLESELECTROWS,
                            ResponseType.MULTISELECTROWS,
                        ]:
                            raise IncorrectPhrasalTemplateItemTypeError()

                        if referenced_item.response_type in [ResponseType.SLIDERROWS] and field.item_index is None:
                            raise IncorrectPhrasalTemplateItemIndexError()

    return values
