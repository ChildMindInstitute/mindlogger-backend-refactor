from gettext import gettext as _

from apps.shared.exception import (
    AccessDeniedError,
    FieldError,
    NotFoundError,
    ValidationError,
)


class ReusableItemChoiceAlreadyExist(ValidationError):
    message = _("Reusable item choice already exist.")


class ReusableItemChoiceDoeNotExist(NotFoundError):
    message = _("Reusable item choice does not exist.")


class ActivityHistoryDoeNotExist(NotFoundError):
    message = _("Activity history does not exist.")


class ActivityDoeNotExist(NotFoundError):
    message = _("Activity does not exist.")


class InvalidVersionError(ValidationError):
    message = _("Invalid version.")


class IncorrectConfigError(FieldError):
    message = _("config must be of type {type}.")


class IncorrectResponseValueError(FieldError):
    message = _("response_values must be of type {type}.")


class IncorrectNameCharactersError(FieldError):
    message = _("Name must contain only alphanumeric symbols or underscore.")


class ScoreRequiredForResponseValueError(FieldError):
    message = _("Score must be provided in each option of response_values.")


class ScoreRequiredForValueError(FieldError):
    message = _("scores must be provided for each value.")


class NullScoreError(FieldError):
    message = _("Score can not be null.")


class DataMatrixRequiredError(FieldError):
    message = _("data_matrix must be provided.")


class CorrectAnswerRequiredError(FieldError):
    message = _(
        "correct_answer must be set if correct_answer_required is True."
    )


class MinValueError(FieldError):
    message = _("Value must be less than max value.")


class InvalidDataMatrixError(FieldError):
    message = _("data_matrix must have the same length as rows")


class InvalidDataMatrixByOptionError(FieldError):
    message = _("data_matrix must have the same length as options")


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
    message = _("Activity access denied")


class DuplicatedActivitiesError(FieldError):
    message = _("Activity ids are duplicated.")


class DuplicateActivityNameError(FieldError):
    message = _("Activity names are duplicated.")


class DuplicateActivityItemNameNameError(FieldError):
    message = _("Activity item names are duplicated.")


class DuplicateActivityFlowNameError(FieldError):
    message = _("Activity flow names are duplicated.")


class DuplicatedActivityFlowsError(FieldError):
    message = _("Activity flow ids are duplicated.")


class IncorrectConditionItemError(FieldError):
    message = _("Condition item does not exist.")


class IncorrectConditionItemIndexError(FieldError):
    message = _("Condition item does not exist.")


class IncorrectConditionOptionError(FieldError):
    message = _("Condition option does not exist.")


class IncorrectConditionLogicItemTypeError(ValidationError):
    message = _("Item type is not supported for conditional logic.")


class HiddenWhenConditionalLogicSetError(ValidationError):
    message = _("Item type cannot be hidden if conditional logic is set.")
