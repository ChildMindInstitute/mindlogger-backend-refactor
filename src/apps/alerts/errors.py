from apps.shared.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class AlertConfigNotFoundError(NotFoundError):
    def __init__(self, *_, message="Alert config not found") -> None:
        super().__init__(message=message)


class ActivityItemNotFoundError(NotFoundError):
    def __init__(self, *_, message="Activity item not found") -> None:
        super().__init__(message=message)


class AlertConfigIsDeletedError(BadRequestError):
    def __init__(self, *_, message="Alert config is deleted") -> None:
        super().__init__(message=message)


class AlertConfigAlreadyExistError(ConflictError):
    def __init__(self, *_, message="Alert config already exist") -> None:
        super().__init__(message=message)


class AlertCreateAccessDenied(ValidationError):
    def __init__(self, *_, message="Access to create alerts denied") -> None:
        super().__init__(message=message)


class AnswerNotFoundError(NotFoundError):
    def __init__(self, *_, message="Answer not found in answers") -> None:
        super().__init__(message=message)
