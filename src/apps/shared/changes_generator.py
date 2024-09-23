"""
Dictionary to generate needed text in one format
"""

_DICTIONARY = dict(
    en=dict(
        added="{0} was added",
        removed="{0} was removed",
        changed="{0} was changed to {1}",
        cleared="{0} was cleared",
        filled="{0} was changed to {1}",
        updated="{0} was updated",
        changed_dict="For {0} language {1} was changed to {2}",
        set_to="{0} was set to {1}",
        set_dict="For {0} language {1} was set to {2}",
        set_bool="{0} option was {1}",
        bool_enabled="{0} was enabled",
        bool_disabled="{0} was disabled",
    )
)

EMPTY_VALUES: tuple = (None, "", 0, dict(), dict(en=""), [])


class ChangeTextGenerator:
    def __init__(self, language="en", dictionary: dict[str, dict] | None = None):
        if dictionary is None:
            dictionary = _DICTIONARY
        self._dictionary = dictionary[language]

    @classmethod
    def is_considered_empty(cls, value) -> bool:
        return value in EMPTY_VALUES

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

    def changed_text(
        self,
        field: str,
        value: str | dict[str, str] | list[str],
        is_initial=False,
    ) -> str:
        """
        Generates text for value chaning or setting if it is initial value.
        """
        # We don't support translations yet
        if isinstance(value, dict):
            v = list(value.values())[0]
        elif isinstance(value, list):
            v = ", ".join(value)
        else:
            v = value
        if is_initial:
            return self._dictionary["set_to"].format(field, v)
        return self._dictionary["filled"].format(field, v)

    def cleared_text(self, field: str) -> str:
        """
        Generates text for clearing field value.
        """
        return self._dictionary["cleared"].format(field)

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

    def set_bool(self, field_name: str, value: bool) -> str:
        """
        Generates text for setting value.
        """
        if value:
            return self._dictionary["bool_enabled"].format(field_name)
        return self._dictionary["bool_disabled"].format(field_name)


class BaseChangeGenerator:
    def __init__(self):
        self._change_text_generator = ChangeTextGenerator()

    def _populate_bool_changes(self, field_name: str, value: bool, changes: list[str]) -> None:
        # Invert value for hidden (UI name contains visibility) because on UI
        # it will be visibility
        if "Visibility" in field_name:
            value = not value
        changes.append(self._change_text_generator.set_bool(field_name, value))
