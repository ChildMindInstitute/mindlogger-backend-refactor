from gettext import gettext as _

from apps.shared.exception import ValidationError


class ActivityAssignmentActivityOrFlowError(ValidationError):
    message = _("Either activity_id or activity_flow_id must be provided, but not both")


class ActivityAssignmentNotActivityAndFlowError(ValidationError):
    message = _("Either activity_id or activity_flow_id must be provided")


class ActivityAssignmentMissingRespondentError(ValidationError):
    message = _("Respondent subject ID must be provided")


class ActivityAssignmentMissingTargetError(ValidationError):
    message = _("Target subject ID must be provided")
