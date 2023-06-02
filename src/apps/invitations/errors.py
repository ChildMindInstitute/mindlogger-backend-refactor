from gettext import gettext as _

from apps.shared.exception import NotFoundError, ValidationError


class InvitationDoesNotExist(NotFoundError):
    message = _("Invitation does not exist.")


class AppletDoesNotExist(ValidationError):
    message = _("Applet does not exist.")


class DoesNotHaveAccess(ValidationError):
    message = _("Access denied.")


class InvitationAlreadyProcesses(ValidationError):
    message = _("Invitation has been already processed.")


class NonUniqueValue(ValidationError):
    message = _("Non-unique value.")


class RespondentDoesNotExist(ValidationError):
    message = _("Respondent does not exist in applet.")


class RespondentsNotSet(ValidationError):
    message = _("Respondents are not set for the reviewer")
