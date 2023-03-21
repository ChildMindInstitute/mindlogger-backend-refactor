from apps.shared.errors import (
    BadRequestError,
    InternalServerError,
    ValidationError,
)


class UserDoesNotHavePermissionError(BadRequestError):
    def __init__(self, *_, message="User does not have permission") -> None:
        super().__init__(message=message)


class AnswerError(InternalServerError):
    def __init__(self, *_, message="Answer error") -> None:
        super().__init__(message=message)


class AnswerIsNotFull(ValidationError):
    def __init__(self, *_, message="Answer is not full."):
        super().__init__(message=message)


class FlowDoesNotHaveActivity(ValidationError):
    def __init__(
        self, *_, message="Activity flow does not have such activity."
    ):
        super().__init__(message=message)
