from gettext import gettext as _

from apps.shared.exception import (
    AccessDeniedError,
    NotFoundError,
    ValidationError,
)


class AlertConfigNotFoundError(NotFoundError):
    message = _("Alert config not found.")


class ActivityItemHistoryNotFoundError(NotFoundError):
    message = _("Activity item history not found.")


class AlertConfigAlreadyExistError(ValidationError):
    message = _("Alert config already exist.")


class AlertCreateAccessDenied(AccessDeniedError):
    message = _("Access to create alerts denied")


class AlertViewAccessDenied(AccessDeniedError):
    message = _("Access to view alerts denied")


class AlertUpdateAccessDenied(AccessDeniedError):
    message = _("Access to update alerts denied")


class AnswerNotFoundError(NotFoundError):
    message = _("Answer not found in answers")


class AlertNotFoundError(NotFoundError):
    message = _("Alert not found")


class AlertIsDeletedError(ValidationError):
    message = _(
        "This alert is deleted. " "The recovery logic is not implemented yet."
    )
