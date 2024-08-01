from gettext import gettext as _

from apps.shared.exception import ValidationError


class ActivityAssignmentActivityOrFlowError(ValidationError):
    message = _("Either activity_id or activity_flow_id must be provided")


class ActivityAssignmentRespondentOrInvitationError(ValidationError):
    message = _("Either respondent_id or invitation_id must be provided")
