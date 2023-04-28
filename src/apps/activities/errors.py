from apps.shared.errors import (
    AccessDeniedError,
    BadRequestError,
    NotFoundError,
    ValidationError,
)


class ReusableItemChoiceAlreadyExist(BadRequestError):
    def __init__(
        self, *_, message="Reusable item choice already exist"
    ) -> None:
        super().__init__(message=message)


class ReusableItemChoiceDoeNotExist(NotFoundError):
    def __init__(
        self, *_, message="Reusable item choice does not exist."
    ) -> None:
        super().__init__(message=message)


class ActivityHistoryDoeNotExist(NotFoundError):
    def __init__(self, *_, message="Activity history does not exist.") -> None:
        super().__init__(message=message)


class InvalidVersionError(ValidationError):
    def __init__(self, *_, message="Invalid version.") -> None:
        super().__init__(message=message)


class ActivityAccessDeniedError(AccessDeniedError):
    def __init__(self, *_, message="Activity access denied") -> None:
        super().__init__(
            message=message,
        )
