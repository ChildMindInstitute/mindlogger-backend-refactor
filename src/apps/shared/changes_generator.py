from apps.activities.domain.activity_item_history import (
    ActivityItemHistoryChange,
)
from apps.activity_flows.domain.flow_history import (
    ActivityFlowItemHistoryChange,
)
from apps.shared.domain.base import to_camelcase

__all__ = ["ChangeTextGenerator", "ChangeGenerator"]

"""
Dictionary to generate needed text in one format
"""
_DICTIONARY = dict(
    en=dict(
        added='"{0}" is added.',
        removed='"{0}" is removed.',
        changed='"{0}" is changed to "{1}".',
        cleared='"{0}" is cleared.',
        filled='"{0}" is updated to "{1}".',
        updated='"{0}" is updated.',
        changed_dict='For {0} language "{1}" is changed to "{2}".',
        set_to='"{0}" is set to "{1}".',
        set_dict='For {0} language "{1}" is set to "{2}".',
        set_bool='"{0}" option was "{1}".',
    )
)

EMPY_VALUES: tuple = (None, "", 0, dict())


class ChangeTextGenerator:
    def __init__(
        self, language="en", dictionary: dict[str, dict] | None = None
    ):
        if dictionary is None:
            dictionary = _DICTIONARY
        self._dictionary = dictionary[language]

    @classmethod
    def is_considered_empty(cls, value) -> bool:
        return value in EMPY_VALUES

    def added_text(self, object_name: str) -> str:
        """
        Generates text for object adding.
        """
        return self._dictionary["added"].format(object_name)

    def removed_text(self, object_name: str) -> str:
        """
        Generates text when object removing.
        """
        return self._dictionary["removed"].format(object_name)

    def changed_text(self, from_, to_) -> str:
        """
        Generates text for value updating.
        """
        return self._dictionary["changed"].format(str(from_), str(to_))

    def changed_dict(self, from_, to_) -> str:
        """
        Generates text of dicts for value updating.
        """
        changes = ""

        # get all keys from both dicts, in set
        keys = set(from_.keys()) | set(to_.keys())
        for key in keys:
            changes += self._dictionary["changed_dict"].format(
                key, from_.get(key, None), to_.get(key, None)
            )

        return changes

    def cleared_text(self, field: str) -> str:
        """
        Generates text for clearing field value.
        """
        return self._dictionary["cleared"].format(field)

    def filled_text(self, field: str, value: str) -> str:
        """
        Generates text for setting value.
        """
        return self._dictionary["filled"].format(field, value)

    def updated_text(self, field: str) -> str:
        """
        Generates text for setting value.
        """
        return self._dictionary["updated"].format(field)

    def set_text(self, field: str, value: str) -> str:
        """
        Generates text for setting value.
        """
        return self._dictionary["set_to"].format(field, value)

    def set_dict(self, field, value) -> str:
        """
        Generates text for setting value.
        """
        changes = ""

        # get all keys from both dicts, in set
        keys = set(value.keys())
        for key in keys:
            changes += self._dictionary["set_dict"].format(
                key, field, value.get(key, None)
            )

        return changes

    def set_bool(self, field: str, value: str) -> str:
        """
        Generates text for setting value.
        """
        return self._dictionary["set_bool"].format(field, value)


class ChangeGenerator:
    def __init__(self):
        self._change_text_generator = ChangeTextGenerator()

    def generate_applet_changes(self, new_applet, old_applet):
        changes = []
        for field, old_value in old_applet.dict().items():
            new_value = getattr(new_applet, field, None)
            if not any([old_value, new_value]):
                continue
            if new_value == old_value:
                continue
            if self._change_text_generator.is_considered_empty(new_value):
                changes.append(
                    self._change_text_generator.cleared_text(
                        to_camelcase(field)
                    ),
                )
            elif self._change_text_generator.is_considered_empty(old_value):
                changes.append(
                    self._change_text_generator.filled_text(
                        to_camelcase(field), new_value
                    ),
                )
            else:
                changes.append(
                    self._change_text_generator.changed_text(
                        f"Applet {field}", new_value
                    )
                    if field not in ["about", "description"]
                    else f"Applet {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, new_value)}."  # noqa: E501
                )

        return changes

    def generate_activity_insert(self, new_activity):
        changes = list()
        for field, value in new_activity.dict().items():
            if field == "name":
                changes.append(
                    self._change_text_generator.set_text(
                        f"Activity {to_camelcase(field)}", value
                    )
                )
            elif field in [
                "id",
                "items",
                "created_at",
                "id_version",
                "applet_id",
                "extra_fields",
            ]:
                continue
            elif field in [
                "scores_and_reports",
                "subscale_setting",
            ]:
                if field == "scores_and_reports":
                    if value:
                        for key, val in value.items():
                            if key in [
                                "generate_report",
                                "show_score_summary",
                            ]:
                                changes.append(
                                    self._change_text_generator.set_bool(
                                        f"Activity {to_camelcase(key)}",
                                        "enabled" if val else "disabled",
                                    )
                                )
                            elif key == "reports":
                                for rep in val:
                                    text = ""
                                    if rep["type"] == "score":
                                        text = f"Activity score {rep['name']}"
                                    elif rep["type"] == "section":
                                        text = (
                                            f"Activity section {rep['name']}"
                                        )
                                    if text == "":
                                        continue
                                    self._change_text_generator.added_text(
                                        text
                                    )

                elif field == "subscale_setting":
                    if value:
                        for key, val in value.items():
                            if key == "subscales":
                                for v in val:
                                    changes.append(
                                        self._change_text_generator.added_text(
                                            f'Activity subscale {v["name"]}'
                                        )
                                    )
                            elif key == "total_scores_table_data":
                                changes.append(
                                    self._change_text_generator.added_text(
                                        f"Activity subscale {to_camelcase(key)}"  # noqa: E501
                                    )
                                )

                            elif key == "calculate_total_score":
                                changes.append(
                                    self._change_text_generator.set_text(
                                        f"Activity subscale {to_camelcase(key)}",  # noqa: E501
                                        val,
                                    )
                                )

            elif isinstance(value, bool):
                changes.append(
                    self._change_text_generator.set_bool(
                        f"Activity {to_camelcase(field)}",
                        "enabled" if value else "disabled",
                    ),
                )
            else:
                if value:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Activity {to_camelcase(field)}", value
                        )
                        if field not in ["description"]
                        else self._change_text_generator.set_dict(
                            f"Activity {to_camelcase(field)}", value
                        ),
                    )
        return changes

    def generate_activity_update(self, new_activity, old_activity):
        changes = list()

        for field, value in new_activity.dict().items():
            old_value = getattr(old_activity, field, None)
            if field in [
                "id",
                "created_at",
                "id_version",
                "applet_id",
                "extra_fields",
                "items",
            ]:
                continue
            elif field in [
                "scores_and_reports",
                "subscale_setting",
            ]:
                if field == "scores_and_reports":
                    if value and value != old_value:
                        for key, val in value.items():
                            old_val = getattr(old_activity, key, None)
                            if key in [
                                "generate_report",
                                "show_score_summary",
                            ]:
                                changes.append(
                                    self._change_text_generator.set_bool(
                                        f"Activity {to_camelcase(key)}",
                                        "enabled" if val else "disabled",
                                    )
                                )
                            elif key == "scores":
                                if val:
                                    old_names = []
                                    if old_val:
                                        old_names = [
                                            old_v.name for old_v in old_val
                                        ]
                                    new_names = [v["name"] for v in val]
                                    deleted_names = list(
                                        set(old_names) - set(new_names)
                                    )
                                    for k, v in enumerate(val):
                                        if v["name"] not in old_names:
                                            changes.append(
                                                self._change_text_generator.added_text(  # noqa: E501
                                                    f'Activity score {v["name"]}'  # noqa: E501
                                                )
                                            )
                                        else:
                                            if (
                                                getattr(
                                                    old_val, k, None
                                                ).dict()
                                                != v.dict()
                                            ):
                                                changes.append(
                                                    self._change_text_generator.changed_text(  # noqa: E501
                                                        f'Activity score {v["name"]}'  # noqa: E501
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(  # noqa: E501
                                                f'Activity scores {", ".join(deleted_names)}'  # noqa: E501
                                            )
                                        )
                                elif old_val:
                                    changes.append(
                                        self._change_text_generator.removed_text(  # noqa: E501
                                            "Activity scores"
                                        )
                                    )

                            elif key == "sections":
                                if val:
                                    old_names = []
                                    if old_val:
                                        old_names = [
                                            old_v.name for old_v in old_val
                                        ]
                                    new_names = [v["name"] for v in val]
                                    deleted_names = list(
                                        set(old_names) - set(new_names)
                                    )

                                    for k, v in enumerate(val):
                                        if v["name"] not in old_names:
                                            changes.append(
                                                self._change_text_generator.added_text(  # noqa: E501
                                                    f'Activity section {v["name"]}'  # noqa: E501
                                                )
                                            )
                                        else:
                                            if (
                                                getattr(
                                                    old_val, k, None
                                                ).dict()
                                                != v.dict()
                                            ):
                                                changes.append(
                                                    self._change_text_generator.changed_text(  # noqa: E501
                                                        f'Activity section {v["name"]}'  # noqa: E501
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(  # noqa: E501
                                                f'Activity section {", ".join(deleted_names)}'  # noqa: E501
                                            )
                                        )
                                elif old_val:
                                    changes.append(
                                        self._change_text_generator.removed_text(  # noqa: E501
                                            "Activity sections"
                                        )
                                    )
                    elif old_value and not value:
                        changes.append(
                            self._change_text_generator.removed_text(
                                f"Activity {to_camelcase(field)}"
                            )
                        )
                elif field == "subscale_setting":
                    if value and value != old_value:
                        for key, val in value.items():
                            old_val = getattr(old_activity, key, None)

                            if key == "subscales":
                                if val:
                                    old_names = []
                                    if old_val:
                                        old_names = [
                                            old_v.name for old_v in old_val
                                        ]
                                    new_names = [v["name"] for v in val]
                                    deleted_names = list(
                                        set(old_names) - set(new_names)
                                    )
                                    for k, v in enumerate(val):
                                        if v["name"] not in old_names:
                                            changes.append(
                                                self._change_text_generator.added_text(  # noqa: E501
                                                    f'Activity subscale {v["name"]}'  # noqa: E501
                                                )
                                            )
                                        else:
                                            if (
                                                getattr(
                                                    old_val, k, None
                                                ).dict()
                                                != v.dict()
                                            ):
                                                changes.append(
                                                    self._change_text_generator.changed_text(  # noqa: E501
                                                        f'Activity subscale {v["name"]}'  # noqa: E501
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(  # noqa: E501
                                                f'Activity subscale {", ".join(deleted_names)}'  # noqa: E501
                                            )
                                        )
                                else:
                                    if old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(  # noqa: E501
                                                "Activity subscales"
                                            )
                                        )
                            else:
                                if val != old_val:
                                    if val and not old_val:
                                        changes.append(
                                            self._change_text_generator.set_text(  # noqa: E501
                                                f"Activity subscale {to_camelcase(key)}",  # noqa: E501
                                                val,
                                            )
                                        )
                                    elif not val and old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(  # noqa: E501
                                                f"Activity subscale {to_camelcase(key)}"  # noqa: E501
                                            )
                                        )
                                    else:
                                        changes.append(
                                            self._change_text_generator.changed_text(  # noqa: E501
                                                f"Activity subscale {to_camelcase(key)}",  # noqa: E501
                                                val,
                                            )
                                        )
                    elif old_value and not value:
                        changes.append(
                            self._change_text_generator.removed_text(
                                f"Activity {to_camelcase(field)}"
                            )
                        )

            elif isinstance(value, bool):
                if value != old_value:
                    changes.append(
                        self._change_text_generator.set_bool(
                            f"Activity {to_camelcase(field)}",
                            "enabled" if value else "disabled",
                        ),
                    )
            else:
                if value != old_value:
                    if field == "description":
                        desc_change = f"Activity {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, value)}."  # noqa: E501
                        changes.append(desc_change)

                    else:
                        changes.append(
                            self._change_text_generator.changed_text(
                                f"Activity {to_camelcase(field)}", value
                            )
                        )
        return changes

    def generate_activity_items_insert(self, items):
        change_items = []
        for item in items:
            change = ActivityItemHistoryChange(
                name=self._change_text_generator.added_text(
                    f"Item {item.name}"
                )
            )
            changes = []
            for field, value in item.dict().items():
                if field == "name":
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Item {to_camelcase(field)}", value
                        )
                    )
                elif field in [
                    "id",
                    "created_at",
                    "id_version",
                    "activity_id",
                    "extra_fields",
                ]:
                    continue
                elif isinstance(value, bool):
                    changes.append(
                        self._change_text_generator.set_bool(
                            f"Item {to_camelcase(field)}",
                            "enabled" if value else "disabled",
                        ),
                    )

                elif field in [
                    "response_values",
                    "config",
                    "conditional_logic",
                ]:
                    if field == "response_values":
                        if value:
                            changes.append(
                                self._change_text_generator.added_text(
                                    f"Item {field}"
                                )
                            )
                    elif field == "config":
                        if value:
                            for key, val in value.items():
                                if isinstance(val, bool):
                                    changes.append(
                                        self._change_text_generator.set_bool(
                                            f"Item {to_camelcase(key)}",
                                            "enabled" if val else "disabled",
                                        )
                                    )

                                elif isinstance(val, dict):
                                    for k, v in val.items():
                                        if isinstance(v, bool):
                                            changes.append(
                                                self._change_text_generator.set_bool(  # noqa: E501
                                                    f"Item {to_camelcase(k)}",
                                                    "enabled"
                                                    if v
                                                    else "disabled",
                                                )
                                            )
                                        else:
                                            changes.append(
                                                self._change_text_generator.added_text(  # noqa: E501
                                                    f"Item {to_camelcase(k)}",
                                                )
                                            )
                                else:
                                    changes.append(
                                        self._change_text_generator.added_text(
                                            f"Item  {to_camelcase(key)}"
                                        )
                                    )
                    else:
                        if value:
                            changes.append(
                                self._change_text_generator.added_text(
                                    f"Item {to_camelcase(field)}"
                                )
                            )

                else:
                    if value:
                        changes.append(
                            self._change_text_generator.set_text(
                                f"Item {to_camelcase(field)}", value
                            )
                            if field not in ["question"]
                            else self._change_text_generator.set_dict(
                                f"Item {to_camelcase(field)}", value
                            ),
                        )

            change.changes = changes
            change_items.append(change)

        return change_items

    def generate_activity_items_update(self, item_groups):
        change_items = []

        for _, (prev_item, new_item) in item_groups.items():
            if not prev_item and new_item:
                change_items.extend(
                    self.generate_activity_items_insert(
                        [
                            new_item,
                        ]
                    )
                )
            elif not new_item and prev_item:
                change_items.append(
                    ActivityItemHistoryChange(
                        name=self._change_text_generator.removed_text(
                            f"Item {prev_item.name}"
                        )
                    )
                )
            elif new_item and prev_item:
                changes = self._generate_activity_item_update(
                    new_item, prev_item
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

    def _generate_activity_item_update(self, new_item, prev_item):
        changes = list()

        for field, value in new_item.dict().items():
            old_value = getattr(prev_item, field, None)
            if field in [
                "id",
                "created_at",
                "id_version",
                "activity_id",
                "extra_fields",
            ]:
                continue
            elif isinstance(value, bool):
                if value != old_value:
                    changes.append(
                        self._change_text_generator.set_bool(
                            f"Item {to_camelcase(field)}",
                            "enabled" if value else "disabled",
                        ),
                    )

            elif field in [
                "response_values",
                "config",
                "conditional_logic",
            ]:
                if field == "response_values":
                    if value and value != old_value:
                        changes.append(
                            self._change_text_generator.added_text(
                                f"Item {field}"
                            )
                        )
                elif field == "config":
                    if value and value != old_value:
                        for key, val in value.items():
                            old_val = getattr(old_value, key, None)
                            if val != old_val:
                                if isinstance(val, bool):
                                    changes.append(
                                        self._change_text_generator.set_bool(
                                            f"Item {to_camelcase(key)}",
                                            "enabled" if val else "disabled",
                                        )
                                    )

                                elif isinstance(val, dict):
                                    for k, v in val.items():
                                        old_v = getattr(old_val, k, None)
                                        if v != old_v:
                                            if isinstance(v, bool):
                                                changes.append(
                                                    self._change_text_generator.set_bool(  # noqa: E501
                                                        f"Item {to_camelcase(k)}",  # noqa: E501
                                                        "enabled"
                                                        if v
                                                        else "disabled",
                                                    )
                                                )
                                            else:
                                                changes.append(
                                                    self._change_text_generator.added_text(  # noqa: E501
                                                        f"Item {to_camelcase(k)}",  # noqa: E501
                                                    )
                                                )
                                else:
                                    changes.append(
                                        self._change_text_generator.added_text(
                                            f"Item  {to_camelcase(key)}"
                                        )
                                    )
                else:
                    if value and not old_value:
                        changes.append(
                            self._change_text_generator.added_text(
                                f"Item {to_camelcase(field)}"
                            )
                        )
                    elif not value and old_value:
                        changes.append(
                            self._change_text_generator.removed_text(
                                f"Item {to_camelcase(field)}"
                            )
                        )
                    elif value != old_value:
                        changes.append(
                            self._change_text_generator.updated_text(
                                f"Item {to_camelcase(field)}"
                            )
                        )

            else:
                if value and value != old_value:
                    changes.append(
                        self._change_text_generator.changed_text(
                            f"Item {to_camelcase(field)}", value
                        )
                        if field not in ["question"]
                        else f"Item {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, value)}."  # noqa: E501
                    )

        return changes

    def generate_flow_insert(self, flow):
        changes = list()
        for field, value in flow.dict().items():
            if field == "name":
                changes.append(
                    self._change_text_generator.set_text(
                        f"Activity Flow {to_camelcase(field)}", value
                    )
                )
            elif field in [
                "id",
                "created_at",
                "id_version",
                "activity_flow_id",
                "activity_id",
                "applet_id",
                "items",
                "extra_fields",
            ]:
                continue
            elif isinstance(value, bool):
                changes.append(
                    self._change_text_generator.set_bool(
                        f"Activity Flow {to_camelcase(field)}",
                        "enabled" if value else "disabled",
                    ),
                )
            else:
                if value:
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Activity Flow {to_camelcase(field)}", value
                        )
                        if field != "description"
                        else self._change_text_generator.set_dict(
                            f"Activity Flow {to_camelcase(field)}", value
                        ),
                    )
        return changes

    def generate_flow_update(self, new_flow, old_flow):
        changes = list()
        for field, value in new_flow.dict().items():
            old_value = getattr(old_flow, field, None)
            if field in [
                "id",
                "created_at",
                "id_version",
                "activity_flow_id",
                "activity_id",
                "applet_id",
                "items",
                "extra_fields",
            ]:
                continue
            elif isinstance(value, bool):
                if value != old_value:
                    changes.append(
                        self._change_text_generator.set_bool(
                            f"Activity Flow {to_camelcase(field)}",
                            "enabled" if value else "disabled",
                        ),
                    )
            else:
                if value != old_value:
                    if field == "description":
                        desc_change = f"Activity Flow {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, value)}."  # noqa: E501
                        changes.append(desc_change)
                    else:
                        changes.append(
                            self._change_text_generator.changed_text(
                                f"Activity Flow {to_camelcase(field)}", value
                            )
                        )
        return changes

    def generate_flow_items_insert(self, flow_items):
        change_items = []
        for item in flow_items:
            change = ActivityFlowItemHistoryChange(
                name=self._change_text_generator.added_text(
                    f"Activity {item.name}"
                )
            )
            changes = []
            for field, value in item.dict().items():
                if field == "order":
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Activity {to_camelcase(field)}", value
                        )
                    )

            change.changes = changes
            change_items.append(change)

        return change_items

    def generate_flow_items_update(self, item_groups):
        change_items = []

        for _, (prev_item, new_item) in item_groups.items():
            if not prev_item and new_item:
                change_items.extend(
                    self.generate_flow_items_insert([new_item])
                )
            elif not new_item and prev_item:
                change_items.append(
                    ActivityFlowItemHistoryChange(
                        name=self._change_text_generator.removed_text(
                            f"Activity {prev_item.name}"
                        )
                    )
                )

        change_items.sort(key=lambda i: i.name, reverse=True)
        return change_items
