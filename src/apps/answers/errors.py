from gettext import gettext as _

from apps.shared.exception import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)


class AnswerNotFoundError(NotFoundError):
    message = _("Answer not found.")


class ReportServerIsNotConfigured(ValidationError):
    message = _("Report server is not configured.")


class AnswerNoteNotFoundError(NotFoundError):
    message = _("Note not found.")


class AnswerAccessDeniedError(AccessDeniedError):
    message = _("Access denied.")


class AnswerNoteAccessDeniedError(AccessDeniedError):
    message = _("Note access denied.")


class AnswerRetentionType(ValidationError):
    message = _("Incorrect answer retention type.")


class UserDoesNotHavePermissionError(AccessDeniedError):
    message = _("User does not have permission.")


class NonPublicAppletError(AccessDeniedError):
    message = _("Access denied. Applet is not public")


class AnswerIsNotFull(ValidationError):
    message = _("Answer is not full.")


class WrongAnswerType(ValidationError):
    message = _("Answer contract is wrong.")


class FlowDoesNotHaveActivity(ValidationError):
    message = _("Activity flow does not have such activity.")


class ActivityDoesNotHaveItem(ValidationError):
    message = _("Activity does not have such item.")


class ActivityIsNotAssessment(ValidationError):
    message = _("Activity is not assessment.")


class ReportServerError(ValidationError):
    message_is_template: bool = True
    message = _("Report server error {message}.")


class WrongAnswerGroupAppletId(ValidationError):
    message = _("In the same submit there can not be different applet id.")


class WrongAnswerGroupVersion(ValidationError):
    message = _("In the same submit there can not be different version.")


class DuplicateActivityInAnswerGroup(ValidationError):
    message = _("Activity answers should differ in the same group.")


class WrongRespondentForAnswerGroup(ValidationError):
    message = _("Different users can not submit with the same submit id.")
