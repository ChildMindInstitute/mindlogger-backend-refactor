from apps.shared import errors


class ActivitiesError(errors.BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Activity service error"
        super().__init__(message or fallback, *args)


class ActivityAlreadyExist(errors.ValidationError):
    def __init__(self, *args) -> None:
        message = "Activity already exists"
        super().__init__(message, *args)


class ReusableItemChoiceAlreadyExist(errors.ValidationError):
    def __init__(self, *args) -> None:
        message = "Reusable item choice already exist"
        super().__init__(message, *args)
