from gettext import gettext as _

from apps.shared.exception import FieldError


class InvalidAuditDateRangeError(FieldError):
    message = _("fromDate must be less than or equal to toDate")
    zero_path = "query"
