from apps.shared.enums import Language
from apps.shared.errors import (
    ValidationError,
)
from apps.shared.exception import NotFoundError, AccessDeniedError


class AnswerNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Answer not found."
    }


class AnswerNoteNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Note not found."
    }


class AnswerAccessDeniedError(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied."
    }


class AnswerNoteAccessDeniedError(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Note access denied."
    }


class UserDoesNotHavePermissionError(AccessDeniedError):
    messages = {
        Language.ENGLISH: "User does not have permission"
    }


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
