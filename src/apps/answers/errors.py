from apps.shared.errors import (
    AccessDeniedError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)


class UserDoesNotHavePermissionError(BadRequestError):
    def __init__(self, *_, message="User does not have permission") -> None:
        super().__init__(message=message)


class AnswerError(InternalServerError):
    def __init__(self, *_, message="Answer error") -> None:
        super().__init__(message=message)


class AnswerNotFoundError(NotFoundError):
    def __init__(self, *_, message="Answer not found.") -> None:
        super().__init__(message=message)


class AnswerNoteNotFoundError(NotFoundError):
    def __init__(self, *_, message="Note not found.") -> None:
        super().__init__(message=message)


class AnswerIsNotFull(ValidationError):
    def __init__(self, *_, message="Answer is not full."):
        super().__init__(message=message)


class WrongAnswerType(ValidationError):
    def __init__(self, *_, message="Answer contract is wrong."):
        super().__init__(message=message)


class FlowDoesNotHaveActivity(ValidationError):
    def __init__(
        self, *_, message="Activity flow does not have such activity."
    ):
        super().__init__(message=message)


class AnswerAccessDeniedError(AccessDeniedError):
    def __init__(self, *_, message="Access denied."):
        super().__init__(message=message)


class AnswerNoteAccessDeniedError(AccessDeniedError):
    def __init__(self, *_, message="Note access denied."):
        super().__init__(message=message)
