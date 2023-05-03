from gettext import gettext as _

from apps.shared.exception import (
    InternalServerError,
    NotFoundError,
    ValidationError,
)


class TransferNotFoundError(NotFoundError):
    message = _("Transfer request not found.")


class TransferError(InternalServerError):
    message = _("Transfer service error.")


class TransferEmailError(ValidationError):
    message = _("Transfer email is incorrect.")
