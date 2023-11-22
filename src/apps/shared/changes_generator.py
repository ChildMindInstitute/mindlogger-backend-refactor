"""
Dictionary to generate needed text in one format
"""
_DICTIONARY = dict(
    en=dict(
        added="{0} is added.",
        removed="{0} is removed.",
        changed="{0} is changed to {1}.",
        cleared="{0} is cleared.",
        filled="{0} is updated to {1}.",
        updated="{0} is updated.",
        changed_dict="For {0} language {1} is changed to {2}.",
        set_to="{0} is set to {1}.",
        set_dict="For {0} language {1} is set to {2}.",
        set_bool="{0} option was {1}.",
    )
)

EMPTY_VALUES: tuple = (None, "", 0, dict(), dict(en=""))


class ChangeTextGenerator:
    def __init__(
        self, language="en", dictionary: dict[str, dict] | None = None
    ):
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


class BaseChangeGenerator:
    def __init__(self):
        self._change_text_generator = ChangeTextGenerator()
