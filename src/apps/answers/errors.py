from gettext import gettext as _

from apps.shared.exception import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)


class AnswerNotFoundError(NotFoundError):
    message = _("Answer not found.")


class AnswerNoteNotFoundError(NotFoundError):
    message = _("Note not found.")


class AnswerAccessDeniedError(AccessDeniedError):
    message = _("Access denied.")


class AnswerNoteAccessDeniedError(AccessDeniedError):
    message = _("Note access denied.")


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
