from gettext import gettext as _

from apps.shared.exception import FieldError


class InvalidAuditDateRangeError(FieldError):
    message = _("fromDatetime must be less than or equal to toDatetime")
    zero_path = "query"
