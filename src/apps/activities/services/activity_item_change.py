import enum
import uuid
from typing import TypeVar

from apps.activities.domain.activity_history import ActivityHistoryFull, ActivityItemHistoryFull
from apps.activities.domain.activity_item_history import ActivityItemHistoryChange
from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.conditions import (
    Condition,
    DateRangePayload,
    MinMaxPayload,
    MinMaxSliderRowPayload,
    MinMaxTimePayload,
    OptionPayload,
    SingleDatePayload,
    SingleTimePayload,
    ValuePayload,
)
from apps.activities.domain.response_type_config import AdditionalResponseOption, ResponseType
from apps.shared.changes_generator import BaseChangeGenerator

GT = TypeVar("GT", ActivityHistoryFull, ActivityItemHistoryFull)
RGT = TypeVar("RGT", None, ActivityHistoryFull, ActivityItemHistoryFull)


class ChangeStatusEnum(str, enum.Enum):
    ADDED = "added"
    UPDATED = "updated"
    REMOVED = "removed"


def group(items: list[GT], new_version: str) -> dict[uuid.UUID, tuple[RGT, RGT]]:
    groups_map: dict = dict()
    for item in items:
        group = groups_map.get(item.id)
        if not group:
            if new_version in item.id_version.split("_"):
                group = (None, item)
            else:
                group = (item, None)
        elif group:
            if new_version in item.id_version.split("_"):
                group = (group[0], item)
            else:
                group = (item, group[1])
        groups_map[item.id] = group

    return groups_map


class ConfigChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "remove_back_button": "Remove Back Button",
        "remove_undo_button": "Remove Undo Button",
        "navigation_to_top": "Navigation To Top",
        "skippable_item": "Skippable Item",
        "play_once": "Play Once",
        "randomize_options": "Randomize Options",
        "show_tick_marks": "Show Tick Marks",
        "show_tick_labels": "Show Tick Marks Labels",
        "continuous_slider": "Use Continius Slider",
        "max_response_length": "Max Response Length",
        "correct_answer_required": "Correct answer required",
        "numerical_response_required": "Numerical Response Required",
        "response_data_identifier": "Response Data Identifier",
        "response_required": "Response Required",
        "correct_answer": "Correct Answer",
        "is_identifier": "Is Identifier",
        "timer": "Timer",
        "add_scores": "Add Scores",
        "set_alerts": "Set Alerts",
        "add_tooltip": "Add Tooltips",
        "set_palette": "Set Color Palette",
        "add_tokens": "Tokens",
        "auto_advance": "Auto Advance",
        # Additional options
        "text_input_option": "Add Text Input Option",
        "text_input_required": "Input Required",
        "portrait_layout": "Portrait Layout",
    }

    def check_changes(self, value, changes: list[str]) -> None:
        if not value:
            return
        for key, val in value:
            if key == "type":
                continue
            if isinstance(val, bool):
                verbose_name = self.field_name_verbose_name_map[key]
                self._populate_bool_changes(verbose_name, val, changes)

            elif isinstance(val, AdditionalResponseOption):
                for k, v in val:
                    verbose_name = self.field_name_verbose_name_map[k]
                    self._populate_bool_changes(verbose_name, v, changes)
            elif val:
                verbose_name = self.field_name_verbose_name_map[key]
                changes.append(self._change_text_generator.set_text(verbose_name, val))

    def check_update_changes(self, old_value, new_value, changes: list[str]) -> None:
        if new_value == old_value:
            return
        for key, val in new_value:
            old_val = getattr(old_value, key)
            if val != old_val:
                if isinstance(val, bool):
                    vn = self.field_name_verbose_name_map[key]
                    self._populate_bool_changes(vn, val, changes)
                elif isinstance(val, AdditionalResponseOption):
                    for k, v in val:
                        old_v = getattr(old_val, k)
                        if v != old_v:
                            vn = self.field_name_verbose_name_map[k]
                            if isinstance(v, bool):
                                self._populate_bool_changes(vn, v, changes)
                elif val != old_val:
                    vn = self.field_name_verbose_name_map[key]
                    changes.append(self._change_text_generator.set_text(vn, val))


class ResponseOptionChangeService(BaseChangeGenerator):
    def check_changes(
        self,
        type_,
        value,
        changes,
    ) -> None:
        if type_ in (ResponseType.SINGLESELECT, ResponseType.MULTISELECT):
            self.__process_container_attr(value, "options", "text", changes)
        elif type_ == ResponseType.SLIDERROWS.value:
            self.__process_container_attr(value, "rows", "label", changes)
        elif type_ in (
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ):
            self.__process_container_attr(value, "rows", "row_name", changes)
            self.__process_container_attr(value, "options", "text", changes)

    def check_changes_update(  # noqa: C901
        self,
        type_,
        old_value,
        new_value,
        changes,
    ) -> None:
        if type_ in (ResponseType.SINGLESELECT, ResponseType.MULTISELECT):
            old_options = old_value.options
            options = {o.id: o for o in new_value.options}
            old_options = {o.id: o for o in old_value.options}
            for k, v in old_options.items():
                new = options.get(k)
                if not new:
                    changes.append(self._change_text_generator.removed_text(f"{v.text} | {v.value} option"))
            for k, v in options.items():
                old = old_options.get(k)
                if not old:
                    changes.append(self._change_text_generator.added_text(f"{v.text} | {v.value} option"))
                elif old.text != v.text:
                    changes.append(
                        self._change_text_generator.changed_text(
                            f"{old.text} | {old.value} option text",
                            f"{v.text} | {v.value}",
                        )
                    )
        elif type_ == ResponseType.SLIDERROWS.value:
            new_rows = {row.id: row.label for row in new_value.rows}
            old_rows = {row.id: row.label for row in old_value.rows}
            for k, v in new_rows.items():
                old_label = old_rows.get(k)
                if not old_label:
                    changes.append(self._change_text_generator.added_text(f"Row {v}"))
                elif old_label != v:
                    changes.append(self._change_text_generator.changed_text(f"Row label {old_label}", v))
            for k, v in old_rows.items():
                new_label = new_rows.get(k)
                if not new_label:
                    changes.append(self._change_text_generator.removed_text(f"Row {v}"))
        elif type_ in (
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ):
            new_rows = {row.id: row.row_name for row in new_value.rows}
            old_rows = {row.id: row.row_name for row in old_value.rows}
            new_options = {o.id: o.text for o in new_value.options}
            old_options = {o.id: o.text for o in old_value.options}
            for k, v in new_rows.items():
                old_row_name = old_rows.get(k)
                if not old_row_name:
                    changes.append(self._change_text_generator.added_text(f"Row {v}"))
                elif old_row_name != v:
                    changes.append(self._change_text_generator.changed_text(f"Row name {old_row_name}", v))
            for k, v in old_rows.items():
                new_row_name = new_rows.get(k)
                if not new_row_name:
                    changes.append(self._change_text_generator.removed_text(f"Row {v}"))
            for k, v in new_options.items():
                old_text = old_options.get(k)
                if not old_text:
                    changes.append(self._change_text_generator.added_text(f"{v} option"))
                elif old_text != v:
                    changes.append(self._change_text_generator.changed_text(f"Option text {old_text}", v))
            for k, v in old_options.items():
                new_text = new_options.get(k)
                if not new_text:
                    changes.append(self._change_text_generator.removed_text(f"{v} option"))

    def __process_container_attr(
        self,
        value,
        container_attr_name: str,
        op_attr_name: str,
        changes: list[str],
    ) -> None:
        container = getattr(value, container_attr_name)
        for i in container:
            name = getattr(i, op_attr_name)
            val = getattr(i, "value", None)
            if container_attr_name == "rows":
                text = f"Row {name}"
            elif val is not None:
                text = f"{name} | {val} option"
            else:
                text = f"{name}"
            changes.append(self._change_text_generator.added_text(text))


class ConditionalLogicChangeService(BaseChangeGenerator):
    def check_changes(
        self,
        parent_field: str,
        value: ConditionalLogic,
        changes: list[str],
        method_name="added_text",
    ) -> None:
        message = f"{parent_field}: If {value.match.capitalize()}: "
        conds: list[str] = []
        for condition in value.conditions:
            condition_type = condition.type.lower().replace("_", " ")
            conds.append(
                f"{condition.item_name} {condition_type} {self.__get_payload(condition)}"  # noqa: E501
            )
        message = message + ", ".join(conds)
        changes.append(getattr(self._change_text_generator, method_name)(message))

    def check_update_changes(
        self,
        parent_field: str,
        old_value: ConditionalLogic | None,
        new_value: ConditionalLogic | None,
        changes: list[str],
    ) -> None:
        if new_value and not old_value:
            self.check_changes(parent_field, new_value, changes)
        elif not new_value and old_value:
            changes.append(self._change_text_generator.removed_text(parent_field))
        # Because we can not check conditional logic identity (there are no
        # any ids or other unique fields) we just write that logic was update
        # to the new value.
        elif new_value != old_value and new_value is not None:
            self.check_changes(
                parent_field,
                new_value,
                changes,
                method_name="updated_text",  # noqa: E501
            )

    @staticmethod
    def __get_payload(condition: Condition) -> str:
        if isinstance(condition.payload, OptionPayload):
            return condition.payload.option_value
        elif isinstance(condition.payload, ValuePayload):
            return str(condition.payload.value)
        elif isinstance(condition.payload, SingleDatePayload):
            return condition.payload.date.isoformat()
        elif isinstance(condition.payload, DateRangePayload):
            if condition.payload.minDate and condition.payload.maxDate:
                return f"Between {condition.payload.minDate.isoformat()} and {condition.payload.maxDate.isoformat()}"
        elif isinstance(condition.payload, MinMaxTimePayload):
            if condition.payload.minTime and condition.payload.maxTime:
                minTime = f"{condition.payload.minTime.hour}:{condition.payload.minTime.minute:02d}"
                maxTime = f"{condition.payload.maxTime.hour}:{condition.payload.maxTime.minute:02d}"
                return f"Between {minTime} and {maxTime}"
        elif isinstance(condition.payload, SingleTimePayload):
            if condition.payload.time:
                return f"{condition.payload.time.hour}:{condition.payload.time.minute:02d}"
        elif isinstance(condition.payload, MinMaxPayload):
            min_value = condition.payload.min_value
            max_value = condition.payload.max_value
            return f"{min_value} and {max_value}"
        elif isinstance(condition.payload, MinMaxSliderRowPayload):
            return f"Between {condition.payload.minValue} and {condition.payload.maxValue}"
        elif hasattr(condition.payload, "value"):
            return str(condition.payload.value)

        return "Unknown"


class ActivityItemChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "name": "Item Name",
        "question": "Displayed Content",
        "response_type": "Item Type",
        "response_values": "Response Options",
        "conditional_logic": "Item Flow",
        "order": "Item Order",
        "is_hidden": "Item Visibility",
        "config": "Settings",
    }

    def __init__(self, old_version: str, new_version: str) -> None:
        self._conf_change_service = ConfigChangeService()
        self._resp_vals_change_service = ResponseOptionChangeService()
        self._cond_logic_change_service = ConditionalLogicChangeService()
        self._old_version = old_version
        self._new_version = new_version
        super().__init__()

    def init_change(self, name: str, state: str) -> ActivityItemHistoryChange:
        match state:
            case ChangeStatusEnum.ADDED:
                method = self._change_text_generator.added_text
            case ChangeStatusEnum.UPDATED:
                method = self._change_text_generator.updated_text
            case ChangeStatusEnum.REMOVED:
                method = self._change_text_generator.removed_text
            case _:
                raise ValueError("Not Suppported State")
        return ActivityItemHistoryChange(name=method((f"Item {name}")))

    def get_changes_insert(self, item: ActivityItemHistoryFull) -> list[str]:
        changes: list[str] = []
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            value = getattr(item, field_name)
            if isinstance(value, bool):
                self._populate_bool_changes(verbose_name, value, changes)
            elif field_name == "response_values":
                self._resp_vals_change_service.check_changes(item.response_type, value, changes)
            elif field_name == "config":
                self._conf_change_service.check_changes(value, changes)
            elif field_name == "conditional_logic":
                if value:
                    self._cond_logic_change_service.check_changes(verbose_name, value, changes)
            elif value:
                changes.append(self._change_text_generator.changed_text(verbose_name, value, is_initial=True))

        return changes

    def get_changes(self, items: list[ActivityItemHistoryFull]) -> list[ActivityItemHistoryChange]:
        grouped = group(items, self._new_version)

        result: list[ActivityItemHistoryChange] = []
        for _, (old_item, new_item) in grouped.items():
            if not old_item and new_item:
                change = self.init_change(new_item.name, ChangeStatusEnum.ADDED)
                change.changes = self.get_changes_insert(new_item)
                result.append(change)
            elif not new_item and old_item:
                change = self.init_change(old_item.name, ChangeStatusEnum.REMOVED)
                result.append(change)
            elif new_item and old_item:
                changes = self.get_changes_update(old_item, new_item)
                if changes:
                    change = self.init_change(new_item.name, ChangeStatusEnum.UPDATED)
                    change.changes = changes
                    result.append(change)

        return result

    def get_changes_update(
        self,
        old_item: ActivityItemHistoryFull,
        new_item: ActivityItemHistoryFull,
    ) -> list[str]:
        changes: list[str] = list()

        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            value = getattr(new_item, field_name)
            old_value = getattr(old_item, field_name)
            if isinstance(value, bool):
                if value != old_value:
                    self._populate_bool_changes(verbose_name, value, changes)
            elif field_name == "response_values":
                self._resp_vals_change_service.check_changes_update(new_item.response_type, old_value, value, changes)
            elif field_name == "config":
                self._conf_change_service.check_update_changes(old_value, value, changes)
            elif field_name == "conditional_logic":
                self._cond_logic_change_service.check_update_changes(verbose_name, old_value, value, changes)
            elif value and value != old_value:
                changes.append(self._change_text_generator.changed_text(verbose_name, value))

        return changes
