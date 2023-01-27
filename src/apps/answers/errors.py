from apps.shared.errors import BadRequestError, InternalServerError


class UserDoesNotHavePermissionError(BadRequestError):
    def __init__(self, *_, message="User does not have permission") -> None:
        super().__init__(message=message)


class AnswerError(InternalServerError):
    def __init__(self, *_, message="Answer error") -> None:
        super().__init__(message=message)
