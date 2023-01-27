from apps.shared.errors import BadRequestError


class UserDoesNotHavePermissionError(BadRequestError):
    def __init__(self, *_, message="User does not have permission") -> None:
        super().__init__(message=message)
