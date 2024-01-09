from gettext import gettext as _

from apps.shared.exception import (
    AccessDeniedError,
    FieldError,
    NotFoundError,
    ValidationError,
)


class InvitationDoesNotExist(NotFoundError):
    message = _("Invitation does not exist.")


class AppletDoesNotExist(ValidationError):
    message = _("Applet does not exist.")


class DoesNotHaveAccess(AccessDeniedError):
    message = _("Access denied.")


class InvitationAlreadyProcessed(ValidationError):
    message = _("Invitation has been already processed.")


class NonUniqueValue(ValidationError):
    message = _("Non-unique value.")


class RespondentDoesNotExist(ValidationError):
    message = _("Respondent does not exist in applet.")


class RespondentsNotSet(ValidationError):
    message = _("Respondents are not set for the reviewer")


class ManagerInvitationExist(FieldError):
    zero_path = "email"
    message = _("User already invited. Edit their access in the Managers tab.")


class RespondentInvitationExist(FieldError):
    zero_path = "email"
    message = _("Respondent already invited.")
