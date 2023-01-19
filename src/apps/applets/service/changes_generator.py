__all__ = ['ChangeTextGenerator']

DICTIONARY = dict(
    en=dict(
        added='New {0} is added.',
        removed='{0} is removed.',
        changed='{0} is changed to {1}.',
        cleared='{0} is cleared.',
        filled='{0} is updated to {0}.',
    )
)

EMPY_VALUES = (None, '', 0)


class ChangeTextGenerator:

    def __init__(
            self, language='en', dictionary: dict[str, dict] | None = None
    ):
        if dictionary is None:
            dictionary = DICTIONARY
        self._dictionary = dictionary[language]

    @classmethod
    def is_considered_empty(cls, value) -> bool:
        return value in EMPY_VALUES

    def added_text(self, object_name: str) -> str:
        """
        Generates text for object adding.
        """
        return self._dictionary['added'].format(object_name)

    def removed_text(self, object_name: str) -> str:
        """
        Generates text when object removing.
        """
        return self._dictionary['removed'].format(object_name)

    def changed_text(self, from_, to_) -> str:
        """
        Generates text for value updating.
        """
        return self._dictionary['changed'].format(str(from_), str(to_))

    def cleared_text(self, field: str) -> str:
        """
        Generates text for clearing field value.
        """
        return self._dictionary['cleared'].format(field)

    def filled_text(self, field: str, value: str) -> str:
        """
        Generates text for setting value.
        """
        return self._dictionary['filled'].format(field, value)
