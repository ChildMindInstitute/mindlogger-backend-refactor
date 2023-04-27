from apps.shared.enums import Language
from apps.shared.exception import NotFoundError, ValidationError, FieldError


class ReusableItemChoiceAlreadyExist(ValidationError):
    messages = {
        Language.ENGLISH: "Reusable item choice already exist."
    }


class ReusableItemChoiceDoeNotExist(NotFoundError):
    messages = {
        Language.ENGLISH: "Reusable item choice does not exist."
    }


class ActivityHistoryDoeNotExist(NotFoundError):
    messages = {
        Language.ENGLISH: "Activity history does not exist."
    }


class InvalidVersionError(ValidationError):
    messages = {
        Language.ENGLISH: "Invalid version."
    }


class IncorrectConfigError(FieldError):
    messages = {
        Language.ENGLISH: "config must be of type {type}"
    }


class IncorrectResponseValueError(FieldError):
    messages = {
        Language.ENGLISH: "response_values must be of type {type}"
    }


class IncorrectNameCharactersError(FieldError):
    messages = {
        Language.ENGLISH: "Name must contain only alphanumeric "
                          "symbols or underscore"
    }


class ScoreRequiredError(FieldError):
    messages = {
        Language.ENGLISH: "Score must be provided in each "
                          "option of response_values"
    }


class NullScoreError(FieldError):
    messages = {
        Language.ENGLISH: "Score can not be null."
    }


class MinValueError(FieldError):
    messages = {
        Language.ENGLISH: "Value must be less than max value."
    }


class InvalidScoreLengthError(FieldError):
    messages = {
        Language.ENGLISH: "Scores must have the same length as the"
                          " range of min_value and max_value"
    }


class InvalidUUIDError(FieldError):
    zero_path = None
    messages = {
        Language.ENGLISH: "Invalid uuid value."
    }


class TimerRequiredError(FieldError):
    zero_path = None
    messages = {
        Language.ENGLISH: "Timer is required for this timer type."
    }


class AtTimeFieldRequiredError(FieldError):
    zero_path = None
    messages = {
        Language.ENGLISH: "at_time is required for this trigger type."
    }


class FromTimeToTimeRequiredError(FieldError):
    zero_path = None
    messages = {
        Language.ENGLISH: "from_time and to_time are required "
                          "for this trigger type."
    }


class ActivityAccessDeniedError(AccessDeniedError):
    def __init__(self, *_, message="Activity access denied") -> None:
        super().__init__(
            message=message,
        )
