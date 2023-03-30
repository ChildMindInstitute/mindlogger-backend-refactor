from apps.shared.errors import (
    AccessDeniedError,
    BadRequestError,
    ConflictError,
    NotFoundError,
)


class AlertConfigNotFoundError(NotFoundError):
    def __init__(self, *_, message="Alert config not found") -> None:
        super().__init__(message=message)


class ActivityItemHistoryNotFoundError(NotFoundError):
    def __init__(self, *_, message="Activity item history not found") -> None:
        super().__init__(message=message)


class AlertConfigAlreadyExistError(ConflictError):
    def __init__(self, *_, message="Alert config already exist") -> None:
        super().__init__(message=message)


class AlertCreateAccessDenied(AccessDeniedError):
    def __init__(self, *_, message="Access to create alerts denied") -> None:
        super().__init__(message=message)


class AlertViewAccessDenied(AccessDeniedError):
    def __init__(self, *_, message="Access to view alerts denied") -> None:
        super().__init__(message=message)


class AlertUpdateAccessDenied(AccessDeniedError):
    def __init__(self, *_, message="Access to update alerts denied") -> None:
        super().__init__(message=message)


class AnswerNotFoundError(NotFoundError):
    def __init__(self, *_, message="Answer not found in answers") -> None:
        super().__init__(message=message)


class AlertNotFoundError(NotFoundError):
    def __init__(self, *_, message="Alert not found") -> None:
        super().__init__(message=message)


class AlertIsDeletedError(BadRequestError):
    def __init__(self, *_, message="Alert is deleted") -> None:
        super().__init__(message=message)
