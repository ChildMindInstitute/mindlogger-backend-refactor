import uuid

from apps.activities.domain.activity_history import ActivityItemHistoryFull
from apps.activities.domain.activity_item_history import (
    ActivityItemHistoryChange,
)
from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.response_type_config import (
    AdditionalResponseOption,
    ResponseType,
)
from apps.shared.changes_generator import (
    BaseChangeGenerator,
    ChangeTextGenerator,
)

Generator = ChangeTextGenerator()


def _process_bool(field_name: str, value: bool, changes: list[str]):
    # Invert value for hidden because on UI it will be visibility
    if field_name in ("Activity Visibility", "Item Visibility"):
        value = not value
    changes.append(Generator.set_bool(field_name, value))


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
        "add_tokens": "tokens",
        # Additional options
        "text_input_option": "Add Text Input Option",
        "text_input_required": "Input Required",
    }

    def check_changes(self, value, changes: list[str]) -> None:
        if not value:
            return
        for key, val in value:
            if isinstance(val, bool):
                verbose_name = self.field_name_verbose_name_map[key]
                _process_bool(verbose_name, val, changes)

            elif isinstance(val, AdditionalResponseOption):
                for k, v in val:
                    verbose_name = self.field_name_verbose_name_map[k]
                    _process_bool(verbose_name, v, changes)
            elif val:
                verbose_name = self.field_name_verbose_name_map[key]
                changes.append(
                    self._change_text_generator.set_text(verbose_name, val)
                )

    def check_update_changes(
        self, old_value, new_value, changes: list[str]
    ) -> None:
        if new_value == old_value:
            return
        for key, val in new_value:
            old_val = getattr(old_value, key)
            if val != old_val:
                if isinstance(val, bool):
                    vn = self.field_name_verbose_name_map[key]
                    _process_bool(vn, val, changes)
                elif isinstance(val, AdditionalResponseOption):
                    for k, v in val:
                        old_v = getattr(old_val, k)
                        if v != old_v:
                            vn = self.field_name_verbose_name_map[key]
                            if isinstance(v, bool):
                                _process_bool(vn, v, changes)
                elif val != old_val:
                    vn = self.field_name_verbose_name_map[key]
                    changes.append(
                        self._change_text_generator.set_text(vn, val)
                    )


class ResponseOptionChangeService(BaseChangeGenerator):
    def check_changes(
        self,
        type_,
        value,
        changes,
    ) -> None:
        if type_ in (
            ResponseType.SINGLESELECT.value,
            ResponseType.MULTISELECT.value,
        ):
            self.__process_container_attr(value, "options", "text", changes)
        elif type_ == ResponseType.SLIDERROWS.value:
            self.__process_container_attr(value, "rows", "label", changes)
        if type_ in (
            ResponseType.SINGLESELECTROWS.value,
            ResponseType.MULTISELECTROWS.value,
        ):
            self.__process_container_attr(value, "rows", "row_name", changes)
            self.__process_container_attr(value, "options", "text", changes)

    def check_changes_update(
        self,
        type_,
        new_value,
        old_value,
        changes,
    ) -> None:
        if type_ in (
            ResponseType.SINGLESELECT.value,
            ResponseType.MULTISELECT.value,
        ):
            old_options = old_value.options
            options = {o.id: o for o in new_value.options}
            old_options = {o.id: o for o in old_value.options}
            for k, v in old_options.items():
                new = options.get(k)
                if not new:
                    changes.append(
                        self._change_text_generator.removed_text(
                            f"{v.text} | {v.value} option"
                        )
                    )
            for k, v in options.items():
                old = old_options.get(k)
                if not old:
                    changes.append(
                        self._change_text_generator.added_text(
                            f"{v.text} | {v.value} option"
                        )
                    )
                elif old.text != v.text:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"{old.text} | {old.value} option",
                            f"{v.text} | {v.value}",
                        )
                    )
        elif type_ == ResponseType.SLIDERROWS.value:
            new_rows = {row.id: row.label for row in new_value.rows}
            old_rows = {row.id: row.label for row in old_value.rows}
            for k, v in new_rows.items():
                old_label = old_rows.get(k)
                if not old_label:
                    changes.append(
                        self._change_text_generator.added_text(f"Row {v}")
                    )
                elif old_label != v:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Row label {old_label}", v
                        )
                    )
            for k, v in old_rows.items():
                new_label = new_rows.get(k)
                if not new_label:
                    changes.append(
                        self._change_text_generator.removed_text(f"Row {v}")
                    )
        if type_ in (
            ResponseType.SINGLESELECTROWS.value,
            ResponseType.MULTISELECTROWS.value,
        ):
            new_rows = {row.id: row.row_name for row in new_value.rows}
            old_rows = {row.id: row.row_name for row in old_value.rows}
            new_options = {o.id: o.text for o in new_value.options}
            old_options = {o.id: o.text for o in old_value.options}
            for k, v in new_rows.items():
                old_row_name = old_rows.get(k)
                if not old_row_name:
                    changes.append(
                        self._change_text_generator.added_text(f"Row {v}")
                    )
                elif old_row_name != v:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Row name {old_row_name}", v
                        )
                    )
            for k, v in old_rows.items():
                new_row_name = new_rows.get(k)
                if not new_row_name:
                    changes.append(
                        self._change_text_generator.removed_text(f"Row {v}")
                    )
            for k, v in new_options.items():
                old_text = old_options.get(k)
                if not old_text:
                    changes.append(
                        self._change_text_generator.added_text(f"{v} option")
                    )
                elif old_text != v:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Option name {old_text}", v
                        )
                    )
            for k, v in old_options.items():
                new_text = new_options.get(k)
                if not new_text:
                    changes.append(
                        self._change_text_generator.removed_text(f"{v} option")
                    )

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
            elif val:
                text = f"{name} | {val} option"
            else:
                text = f"{name}"
            changes.append(self._change_text_generator.added_text(text))


class ActivityItemChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "name": "Item Name",
        "question": "Displayed Content",
        "response_type": "Item Type",
        "response_values": "Response Options",
        "conditional_logic": "Item Flow",
        "order": "Item Order",
        "is_hidden": "Item Visibility",
    }

    def __init__(self) -> None:
        self._conf_change_service = ConfigChangeService()
        self._resp_vals_change_service = ResponseOptionChangeService()
        super().__init__()

    def _init_change(self, item_name: str) -> ActivityItemHistoryChange:
        return ActivityItemHistoryChange(
            name=self._change_text_generator.added_text(f"Item {item_name}")
        )

    def generate_activity_items_insert(
        self, items: list[ActivityItemHistoryFull]
    ) -> list[ActivityItemHistoryChange]:
        change_items: list[ActivityItemHistoryChange] = []
        for item in items:
            change = self._init_change(item.name)
            changes: list[str] = []
            for (
                field_name,
                verbose_name,
            ) in self.field_name_verbose_name_map.items():
                value = getattr(item, field_name)
                if isinstance(value, bool):
                    _process_bool(verbose_name, value, changes)
                elif field_name == "response_values":
                    self._resp_vals_change_service.check_changes(
                        item.response_type, value, changes
                    )
                # Check name, because type of value can be different
                elif field_name == "config":
                    self._conf_change_service.check_changes(value, changes)
                elif isinstance(value, ConditionalLogic):
                    if value:
                        changes.append(
                            self._change_text_generator.added_text(
                                verbose_name
                            )
                        )
                elif value:
                    changes.append(
                        self._change_text_generator.changed_text(
                            verbose_name, value, is_initial=True
                        )
                    )

            change.changes = changes
            change_items.append(change)

        return change_items

    def generate_activity_items_update(
        self,
        item_groups: dict[
            uuid.UUID,
            tuple[
                ActivityItemHistoryFull | None, ActivityItemHistoryFull | None
            ],
        ],
    ) -> list[ActivityItemHistoryChange]:
        change_items: list[ActivityItemHistoryChange] = []

        for _, (old_item, new_item) in item_groups.items():
            if not old_item and new_item:
                change_items += self.generate_activity_items_insert([new_item])
            elif not new_item and old_item:
                change_items.append(
                    ActivityItemHistoryChange(
                        name=self._change_text_generator.removed_text(
                            f"Item {old_item.name}"
                        )
                    )
                )
            elif new_item and old_item:
                changes = self._generate_activity_item_update(
                    new_item, old_item
                )
                if changes:
                    change_items.append(
                        ActivityItemHistoryChange(
                            name=self._change_text_generator.updated_text(
                                f"Item {new_item.name}",
                            ),
                            changes=changes,
                        )
                    )

        return change_items

    def _generate_activity_item_update(
        self,
        new_item: ActivityItemHistoryFull,
        old_item: ActivityItemHistoryFull,
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
                    _process_bool(verbose_name, value, changes)
            elif field_name == "response_values":
                self._resp_vals_change_service.check_changes_update(
                    new_item.response_type, value, old_value, changes
                )
            elif field_name == "config":
                self._conf_change_service.check_update_changes(
                    old_value, value, changes
                )
            elif isinstance(value, ConditionalLogic):
                if value and not old_value:
                    changes.append(
                        self._change_text_generator.added_text(verbose_name)
                    )
                elif not value and old_value:
                    changes.append(
                        self._change_text_generator.removed_text(verbose_name)
                    )
                elif value != old_value:
                    changes.append(
                        self._change_text_generator.updated_text(verbose_name)
                    )

            elif value and value != old_value:
                changes.append(
                    self._change_text_generator.changed_text(
                        verbose_name, value
                    )
                )

        return changes
