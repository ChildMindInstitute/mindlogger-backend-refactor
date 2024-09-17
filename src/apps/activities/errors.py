from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, FieldError, NotFoundError, ValidationError


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
    message_is_template: bool = True
    message = _("config must be of type {type}.")


class IncorrectResponseValueError(FieldError):
    message_is_template: bool = True
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
    message = _("correct_answer must be set if correct_answer_required is True.")


class MinValueError(FieldError):
    message = _("min value must be less than max value.")


class SliderValueError(FieldError):
    message = _("Either value or min_value and max_value must be set.")


class SliderMinMaxValueError(FieldError):
    message = _(
        "If continuous_slider is checked, min_value and max_value must be set. If not, then value must be set."  # noqa: E501
    )


class SliderRowsValueError(FieldError):
    message = _("Only value must be set.")


class AlertFlagMissingSingleMultiRowItemError(FieldError):
    message = _(
        "set_alerts flag is not set for (single, multi selection) items with alerts."  # noqa: E501
    )


class AlertFlagMissingSliderItemError(FieldError):
    message = _("set_alerts flag is not set for slider(rows) items with alerts.")


class InvalidDataMatrixError(FieldError):
    message = _("data_matrix must have the same length as rows")


class InvalidDataMatrixByOptionError(FieldError):
    message = _("data_matrix must have the same length as options")


class InvalidScoreLengthError(FieldError):
    message = _("Scores must have the same length as the " "range of min_value and max_value")


class ActivityAccessDeniedError(AccessDeniedError):
    message = _("Activity access denied")


class DuplicatedActivitiesError(FieldError):
    message = _("Activity ids are duplicated.")


class DuplicateActivityNameError(FieldError):
    message = _("Activity names are duplicated.")


class AssessmentLimitExceed(FieldError):
    message = _("Assessments count can not be more than one.")


class DuplicateActivityItemNameNameError(FieldError):
    message = _("Activity item names are duplicated.")


class DuplicateActivityFlowNameError(FieldError):
    message = _("Activity flow names are duplicated.")


class DuplicatedActivityFlowsError(FieldError):
    message = _("Activity flow ids are duplicated.")


class IncorrectConditionItemError(FieldError):
    message = _("Condition item does not exist.")


class IncorrectScoreItemError(FieldError):
    message = _("Score item does not exist.")


class IncorrectScorePrintItemError(FieldError):
    message = _("Score print item does not exist.")


class IncorrectSectionPrintItemError(FieldError):
    message = _("Section print item does not exist.")


class IncorrectConditionItemIndexError(ValidationError):
    message = _(
        " Selected position of the Item in the list contradicts the Item Flow."
        # noqa: E501
    )


class IncorrectConditionOptionError(FieldError):
    message = _("Condition option does not exist.")


class IncorrectConditionLogicItemTypeError(ValidationError):
    message = _("Item type is not supported for conditional logic.")


class IncorrectScoreItemTypeError(ValidationError):
    message = _("Item type is not supported for score setting.")


class IncorrectScorePrintItemTypeError(ValidationError):
    message = _("Item type is not supported for score print setting.")


class IncorrectSectionPrintItemTypeError(ValidationError):
    message = _("Item type is not supported for section print setting.")


class IncorrectSectionConditionItemError(ValidationError):
    message = _("Section condition item does not exist.")


class IncorrectScoreItemConfigError(ValidationError):
    message = _("Item config is not supported for score setting.")


class HiddenWhenConditionalLogicSetError(ValidationError):
    message = _("Item type cannot be hidden if conditional logic is set.")


class DuplicateScoreNameError(FieldError):
    message = _("Score names are duplicated.")


class DuplicateSectionNameError(FieldError):
    message = _("Section names are duplicated.")


class DuplicateScoreIdError(FieldError):
    message = _("Score ids are duplicated.")


class DuplicateScoreItemNameError(FieldError):
    message = _("Score item names are duplicated.")


class DuplicateScoreConditionNameError(FieldError):
    message = _("Score condition names are duplicated.")


class DuplicateScoreConditionIdError(FieldError):
    message = _("Score condition ids are duplicated.")


class ScoreConditionItemNameError(FieldError):
    message = _("The item_name field in conditions must be same as score id.")


class PeriodIsRequiredError(ValidationError):
    message = _("Period field is required.")


class InvalidRawScoreSubscaleError(ValidationError):
    message = _("Raw score in subscale table is invalid.")


class InvalidScoreSubscaleError(ValidationError):
    message = _("Score in subscale lookup table is invalid.")

class InvalidAgeSubscaleError(ValidationError):
    message = _("Age in subscale lookup table is invalid.")


class IncorrectSubscaleItemError(ValidationError):
    message = _("Activity item inside subscale does not exist.")


class IncorrectSubscaleInsideSubscaleError(ValidationError):
    message = _("Subscale referred inside subscale does not exist.")


class SubscaleInsideSubscaleError(ValidationError):
    message = _("Subscale cannot refer to itself inside items.")


class SubscaleItemScoreError(ValidationError):
    message = _("Score must be provided for activity item inside subscale.")


class SubscaleItemTypeError(ValidationError):
    message = _("Activity item inside subscale must be of type singleselect, multiselect or slider.")


class DuplicateSubscaleNameError(FieldError):
    message = _("Subscale names are duplicated.")


class FlowItemActivityKeyNotFoundError(ValidationError):
    message = _("Activity key from activity flow item is not found in activity list.")


class MultiSelectNoneOptionError(ValidationError):
    message = _("No more than 1 none option is not allowed for multiselect.")


class FlowDoesNotExist(NotFoundError):
    message = _("Flow does not exist.")


class IncorrectPhrasalTemplateItemError(ValidationError):
    message = _("Activity item inside phrasal template does not exist.")


class IncorrectPhrasalTemplateItemTypeError(ValidationError):
    message = _("Invalid type for activity item inside phrasal template")


class IncorrectPhrasalTemplateItemIndexError(ValidationError):
    message = _("Invalid item index for activity item inside phrasal template")
