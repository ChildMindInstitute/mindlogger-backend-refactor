from apps.applets.domain import AppletHistoryChange
from apps.activities.domain import ActivityHistoryChange
from apps.shared.domain.base import to_camelcase

__all__ = ["ChangeTextGenerator"]

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
        changes_applet = AppletHistoryChange(
            display_name=new_applet.display_name
        )
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
                        old_value, new_value
                    )
                    if field not in ["about", "description"]
                    else f"Applet {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, new_value)}."
                )

        changes_applet.changes = changes

        return changes_applet

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
                "created_at",
                "id_version",
                "applet_id",
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
                            elif key == "scores":
                                for v in val:
                                    changes.append(
                                        self._change_text_generator.added_text(
                                            f'Activity score {v["name"]}'
                                        )
                                    )
                            elif key == "sections":
                                for v in val:
                                    changes.append(
                                        self._change_text_generator.added_text(
                                            f'Activity section {v["name"]}'
                                        )
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
                                        f"Activity subscale {to_camelcase(key)}"
                                    )
                                )

                            elif key == "calculate_total_score":
                                changes.append(
                                    self._change_text_generator.set_text(
                                        f"Activity subscale {to_camelcase(key)}",
                                        val,
                                    )
                                )

            elif type(value) == bool:
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
            ]:
                continue
            elif field in [
                "scores_and_reports",
                "subscale_setting",
            ]:
                if field == "scores_and_reports":
                    if value:
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
                                                self._change_text_generator.added_text(
                                                    f'Activity score {v["name"]}'
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
                                                    self._change_text_generator.changed_text(
                                                        f'Activity score {v["name"]}'
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f'Activity scores {", ".join(deleted_names)}'
                                            )
                                        )
                                else:
                                    if old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f"Activity scores"
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
                                                self._change_text_generator.added_text(
                                                    f'Activity section {v["name"]}'
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
                                                    self._change_text_generator.changed_text(
                                                        f'Activity section {v["name"]}'
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f'Activity section {", ".join(deleted_names)}'
                                            )
                                        )
                                else:
                                    if old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f"Activity sections"
                                            )
                                        )
                    else:
                        if old_value:
                            changes.append(
                                self._change_text_generator.removed_text(
                                    f"Activity {to_camelcase(field)}"
                                )
                            )
                elif field == "subscale_setting":
                    if value:
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
                                                self._change_text_generator.added_text(
                                                    f'Activity subscale {v["name"]}'
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
                                                    self._change_text_generator.changed_text(
                                                        f'Activity subscale {v["name"]}'
                                                    )
                                                )

                                    if deleted_names:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f'Activity subscale {", ".join(deleted_names)}'
                                            )
                                        )
                                else:
                                    if old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f"Activity subscales"
                                            )
                                        )
                            else:
                                if val != old_val:
                                    if val and not old_val:
                                        changes.append(
                                            self._change_text_generator.set_text(
                                                f"Activity subscale {to_camelcase(key)}",
                                                val,
                                            )
                                        )
                                    elif not val and old_val:
                                        changes.append(
                                            self._change_text_generator.removed_text(
                                                f"Activity subscale {to_camelcase(key)}"
                                            )
                                        )
                                    else:
                                        changes.append(
                                            self._change_text_generator.changed_text(
                                                f"Activity subscale {to_camelcase(key)}",
                                                val,
                                            )
                                        )
                    else:
                        if old_value:
                            changes.append(
                                self._change_text_generator.removed_text(
                                    f"Activity {to_camelcase(field)}"
                                )
                            )

            elif type(value) == bool:
                changes.append(
                    self._change_text_generator.set_bool(
                        f"Activity {to_camelcase(field)}",
                        "enabled" if value else "disabled",
                    ),
                )
            else:
                if value:
                    if field == "description":
                        desc_change = f"Activity {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, value)}."  # noqa: E501
                        changes.append(desc_change)

                    else:
                        changes.append(
                            self._change_text_generator.changed_text(
                                f"Activity {to_camelcase(field)}", value
                            )
                        )
        return changes, bool(changes)
