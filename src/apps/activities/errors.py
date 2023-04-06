from apps.shared.errors import BadRequestError, NotFoundError, ValidationError


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


class InvalidVersionError(ValidationError):
    def __init__(self, *_, message="Invalid version.") -> None:
        super().__init__(message=message)
