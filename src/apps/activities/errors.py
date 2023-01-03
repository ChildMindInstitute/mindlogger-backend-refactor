import apps.shared.errors as general_errors


class ActivitiesError(general_errors.BaseError):
    def __init__(self, message="", *args) -> None:
        fallback = "Activity service error"
        super().__init__(message or fallback, *args)


class ActivityAlreadyExist(general_errors.ValidationError):
    def __init__(self, *args) -> None:
        message = "Activity already exists"
        super().__init__(message, *args)


class ReusableItemChoiceAlreadyExist(general_errors.ValidationError):
    def __init__(self, *args) -> None:
        message = "Reusable item choice already exist"
        super().__init__(message, *args)
