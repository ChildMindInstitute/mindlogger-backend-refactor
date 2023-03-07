from apps.shared.errors import (
    BadRequestError,
    BaseError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)


class UsersError(BaseError):
    def __init__(self, *_, message="Users error") -> None:
        super().__init__(message=message)


class UserAlreadyExistError(ConflictError):
    def __init__(self, *_, message="User already exist") -> None:
        super().__init__(message=message)


class UserNotFound(NotFoundError):
    def __init__(self, *_, message="User not found") -> None:
        super().__init__(message=message)


class UserIsDeletedError(BadRequestError):
    def __init__(self, *_, message="User is deleted") -> None:
        super().__init__(message=message)


class EmailAddressError(InternalServerError):
    def __init__(self, *_, message="Email address not found") -> None:
        super().__init__(message=message)
