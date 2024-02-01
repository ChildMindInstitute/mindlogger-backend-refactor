from apps.activities.domain.activity_history import (
    ActivityHistoryChange,
    ActivityHistoryFull,
)
from apps.activities.domain.scores_reports import (
    Score,
    ScoresAndReports,
    Section,
    SubscaleCalculationType,
    SubscaleSetting,
)
from apps.activities.services.activity_item_change import (
    ActivityItemChangeService,
    ChangeStatusEnum,
    group,
)
from apps.shared.changes_generator import EMPTY_VALUES, BaseChangeGenerator


class ScoresAndReportsChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "generate_report": "Scores & Reports: Generate Report",
        "show_score_summary": "Scores & Reports: Show Score Summary",
        # TODO: Add separate ChangeService for reports attrs
        "score": "Scores & Reports: Score",
        "section": "Scores & Reports: Section",
    }

    def check_changes(
        self,
        value: ScoresAndReports | None,
        changes: list[str],
    ) -> None:
        # Possible this case is unavailable, but model parent model declared
        # this field as optional
        if not value:
            return
        for key, val in value:
            if isinstance(val, bool):
                verbose_name = self.field_name_verbose_name_map[key]
                self._populate_bool_changes(verbose_name, val, changes)
            else:
                for rep in val:
                    verbose_name = self.field_name_verbose_name_map[rep.type]
                    vn = f"{verbose_name} {rep.name}"
                    changes.append(self._change_text_generator.added_text(vn))

    def check_update_changes(
        self,
        parent_field_name: str,
        old_value: ScoresAndReports | None,
        value: ScoresAndReports | None,
        changes: list[str],
    ) -> None:
        if value and not old_value:
            self.check_changes(value, changes)
        # Possible this case is not allowed from UI, but need to be ready
        elif not value and old_value:
            changes.append(
                self._change_text_generator.removed_text(parent_field_name)
            )
        elif value and value != old_value:
            for key, val in value:
                old_val = getattr(old_value, key)
                if isinstance(val, bool):
                    vn = self.field_name_verbose_name_map[key]
                    self._populate_bool_changes(vn, val, changes)
                elif key == "reports":
                    self.__check_for_changes(val, old_val, "score", changes)
                    self.__check_for_changes(val, old_val, "section", changes)

    def __check_for_changes(
        self,
        value: list[Score | Section],
        old_value: list[Score | Section],
        type_: str,
        changes: list[str],
    ) -> None:
        # Assumption: names are unique
        old = {v.name: v for v in old_value if v.type == type_}
        new = {v.name: v for v in value if v.type == type_}
        deleted = list(set(old) - set(new))
        inseted = list(set(new) - set(old))
        vn = self.field_name_verbose_name_map[type_]
        for k, v in new.items():
            old_v = old.get(k)
            if old_v and old_v != v:
                changes.append(
                    self._change_text_generator.updated_text(f"{vn} {v.name}")
                )
        for name in deleted:
            changes.append(
                self._change_text_generator.removed_text(f"{vn} {name}")
            )
        for name in inseted:
            changes.append(
                self._change_text_generator.added_text(f"{vn} {name}")
            )


class SubscaleSettingChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "calculate_total_score": "Subscale Configuration: Calculate total score",  # noqa E501
        "subscales": "Subscale Configuration: Subscale",
        "total_scores_table_data": "Subscale Configuration: Total Scores Table Data",  # noqa E501
    }
    verbose_total_score_map = {
        "sum": "Sum of Item Scores",
        "average": "Average of Item Scores",
    }

    def check_changes(
        self,
        value: SubscaleSetting | None,
        changes: list[str],
    ) -> None:
        if not value:
            return
        for key, val in value:
            vn = self.field_name_verbose_name_map[key]
            if isinstance(val, list):
                for v in val:
                    changes.append(
                        self._change_text_generator.added_text(
                            f"{vn} {v.name}"
                        )
                    )
            elif isinstance(val, SubscaleCalculationType):
                changes.append(
                    self._change_text_generator.set_text(
                        vn, self.verbose_total_score_map[val]
                    )
                )
            else:
                changes.append(self._change_text_generator.added_text(vn))

    def check_update_changes(
        self,
        parent_field_name: str,
        old_value: SubscaleSetting | None,
        value: SubscaleSetting | None,
        changes: list[str],
    ) -> None:
        if value and not old_value:
            self.check_changes(value, changes)
        elif not value and old_value:
            changes.append(
                self._change_text_generator.removed_text(parent_field_name)
            )
        elif value and value != old_value:
            for key, val in value:
                old_val = getattr(old_value, key)
                vn = self.field_name_verbose_name_map[key]
                if key == "subscales":
                    # Assumption: names are unique
                    old_scales_map = {v.name: v for v in old_val}
                    new_scales_map = {v.name: v for v in val}
                    inserted_scales = list(
                        set(new_scales_map) - set(old_scales_map)
                    )
                    deleted_scales = list(
                        set(old_scales_map) - set(new_scales_map)
                    )
                    for k, v in new_scales_map.items():
                        old_v = old_scales_map.get(k)
                        if old_v and old_v != v:
                            changes.append(
                                self._change_text_generator.updated_text(
                                    f"{vn} {k}"
                                )
                            )
                    for name in deleted_scales:
                        changes.append(
                            self._change_text_generator.removed_text(
                                f"{vn} {name}"
                            )
                        )
                    for name in inserted_scales:
                        changes.append(
                            self._change_text_generator.added_text(
                                f"{vn} {name}"
                            )
                        )

                elif key == "calculate_total_score":
                    verbose_value_map = {
                        "sum": "Sum of Item Scores",
                        "average": "Average of Item Scores",
                    }
                    if val and val != old_val:
                        changes.append(
                            self._change_text_generator.set_text(
                                vn, verbose_value_map[val]
                            )
                        )
                    elif val:
                        changes.append(
                            self._change_text_generator.set_text(
                                vn, verbose_value_map[val]
                            )
                        )
                    elif old_val:
                        changes.append(
                            self._change_text_generator.removed_text(vn)
                        )


class ActivityChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "name": "Activity Name",
        "description": "Activity Description",
        "splash_screen": "Splash Screen",
        "image": "Activity Image",
        "order": "Activity Order",
        "show_all_at_once": "Show all questions at once",
        "is_skippable": "Allow to skip all items",
        "is_reviewable": "Turn the Activity to the Reviewer dashboard assessment",  # noqa E501
        "response_is_editable": "Disable the respondent's ability to change the response",  # noqa E501
        "report_included_item_name": "Report's name included item name",
        # NOTE: is_hidden should be inverted
        "is_hidden": "Activity Visibility",
        "scores_and_reports": "Scores & Reports option",
        "subscale_setting": "Subscale Setting option",
    }

    def __init__(self, old_version: str, new_version: str) -> None:
        self._sar_service = ScoresAndReportsChangeService()
        self._scale_service = SubscaleSettingChangeService()
        self._old_version = old_version
        self._new_version = new_version
        super().__init__()

    def init_change(self, name: str, state: str) -> ActivityHistoryChange:
        match state:
            case ChangeStatusEnum.ADDED:
                method = self._change_text_generator.added_text
            case ChangeStatusEnum.UPDATED:
                method = self._change_text_generator.updated_text
            case ChangeStatusEnum.REMOVED:
                method = self._change_text_generator.removed_text
            case _:
                raise ValueError("Not Suppported State")
        return ActivityHistoryChange(name=method((f"Activity {name}")))

    def get_changes(
        self, activities: list[ActivityHistoryFull]
    ) -> list[ActivityHistoryChange]:
        grouped = group(activities, self._new_version)
        item_service = ActivityItemChangeService(
            self._old_version, self._new_version
        )
        result: list[ActivityHistoryChange] = []
        for _, (old_activity, new_activity) in grouped.items():
            if not old_activity and new_activity:
                change = self.init_change(
                    new_activity.name, ChangeStatusEnum.ADDED
                )
                change.changes = self.get_changes_insert(new_activity)
                change.items = item_service.get_changes(new_activity.items)
                result.append(change)
            elif not new_activity and old_activity:
                change = self.init_change(
                    old_activity.name, ChangeStatusEnum.REMOVED
                )
                result.append(change)
            elif new_activity and old_activity:
                changes = self.get_changes_update(old_activity, new_activity)
                changes_items = item_service.get_changes(
                    old_activity.items + new_activity.items
                )

                if changes or changes_items:
                    change = self.init_change(
                        new_activity.name,
                        ChangeStatusEnum.UPDATED,
                    )
                    change.changes = changes
                    change.items = changes_items
                    result.append(change)
        return result

    def get_changes_insert(
        self, new_activity: ActivityHistoryFull
    ) -> list[str]:
        changes: list[str] = list()
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            value = getattr(new_activity, field_name)
            if isinstance(value, ScoresAndReports):
                self._sar_service.check_changes(value, changes)
            elif isinstance(value, SubscaleSetting):
                self._scale_service.check_changes(value, changes)
            elif isinstance(value, bool):
                self._populate_bool_changes(verbose_name, value, changes)
            elif value not in EMPTY_VALUES:
                changes.append(
                    self._change_text_generator.changed_text(
                        verbose_name, value, is_initial=True
                    )
                )
        return changes

    def get_changes_update(
        self,
        old_activity: ActivityHistoryFull,
        new_activity: ActivityHistoryFull,
    ) -> list[str]:
        changes: list[str] = list()
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            value = getattr(new_activity, field_name)
            old_value = getattr(old_activity, field_name)
            if field_name == "scores_and_reports":
                self._sar_service.check_update_changes(
                    verbose_name, old_value, value, changes
                )
            elif field_name == "subscale_setting":
                self._scale_service.check_update_changes(
                    verbose_name, old_value, value, changes
                )
            elif isinstance(value, bool):
                if value != old_value:
                    self._populate_bool_changes(verbose_name, value, changes)
            elif value != old_value:
                is_initial = old_value in EMPTY_VALUES
                changes.append(
                    self._change_text_generator.changed_text(
                        verbose_name, value, is_initial=is_initial
                    )
                )
        return changes
