from gettext import gettext as _

from apps.shared.exception import FieldError, NotFoundError, ValidationError


class ReusableItemChoiceAlreadyExist(ValidationError):
    message = _("Reusable item choice already exist.")


class ReusableItemChoiceDoeNotExist(NotFoundError):
    message = _("Reusable item choice does not exist.")


class ActivityHistoryDoeNotExist(NotFoundError):
    message = _("Activity history does not exist.")


class InvalidVersionError(ValidationError):
    message = _("Invalid version.")


class IncorrectConfigError(FieldError):
    message = _("config must be of type {type}")


class IncorrectResponseValueError(FieldError):
    message = _("response_values must be of type {type}")


class IncorrectNameCharactersError(FieldError):
    message = _("Name must contain only alphanumeric symbols or underscore")


class ScoreRequiredError(FieldError):
    message = _("Score must be provided in each option of response_values")


class NullScoreError(FieldError):
    message = _("Score can not be null.")


class MinValueError(FieldError):
    message = _("Value must be less than max value.")


class InvalidScoreLengthError(FieldError):
    message = _(
        "Scores must have the same length as the "
        "range of min_value and max_value"
    )


class InvalidUUIDError(FieldError):
    zero_path = None
    message = _("Invalid uuid value.")


class TimerRequiredError(FieldError):
    zero_path = None
    message = _("Timer is required for this timer type.")


class AtTimeFieldRequiredError(FieldError):
    zero_path = None
    message = _("at_time is required for this trigger type.")


class FromTimeToTimeRequiredError(FieldError):
    zero_path = None
    message = _("from_time and to_time are required for this trigger type.")


class ActivityAccessDeniedError(AccessDeniedError):
    def __init__(self, *_, message="Activity access denied") -> None:
        super().__init__(
            message=message,
        )
