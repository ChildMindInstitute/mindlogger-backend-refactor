from apps.shared.enums import Language
from apps.shared.exception import ValidationError, NotFoundError, \
    AccessDeniedError


class AlertConfigNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Alert config not found."
    }


class ActivityItemHistoryNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Activity item history not found."
    }


class AlertConfigAlreadyExistError(ValidationError):
    messages = {Language.ENGLISH: "Alert config already exist."}


class AlertCreateAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access to create alerts denied"
    }


class AlertViewAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access to view alerts denied"
    }


class AlertUpdateAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access to update alerts denied"
    }


class AnswerNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Answer not found in answers"
    }


class AlertNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Alert not found"
    }


class AlertIsDeletedError(ValidationError):
    messages = {
        Language.ENGLISH: "This alert is deleted. "
                          "The recovery logic is not implemented yet."
    }
